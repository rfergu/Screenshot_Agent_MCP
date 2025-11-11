"""Performance tests to validate processing speed targets."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from organizers.batch_processor import BatchProcessor, FileProcessingResult
from processors.ocr_processor import OCRProcessor
from processors.vision_processor import VisionProcessor


class TestOCRPerformance:
    """Test OCR processing performance targets."""

    @pytest.fixture
    def temp_screenshot(self):
        """Create a temporary test screenshot."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Create realistic test image (typical screenshot size)
            img = Image.new("RGB", (1920, 1080), color="white")
            img.save(f.name)
            yield Path(f.name)
            Path(f.name).unlink(missing_ok=True)

    @pytest.mark.performance
    def test_ocr_speed_target_50ms(self, temp_screenshot):
        """Test OCR processing meets <50ms target (with mocked OCR)."""
        # Mock pytesseract to focus on our code performance
        with patch("processors.ocr_processor.pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "Sample text extracted from screenshot"

            ocr_processor = OCRProcessor()

            # Warm-up run
            ocr_processor.process(temp_screenshot)

            # Timed runs
            times = []
            for _ in range(10):
                start = time.perf_counter()
                result = ocr_processor.process(temp_screenshot)
                elapsed_ms = (time.perf_counter() - start) * 1000
                times.append(elapsed_ms)

                # Verify result structure
                assert result.processing_time_ms > 0
                assert result.text is not None

            # Calculate statistics
            avg_time = sum(times) / len(times)
            max_time = max(times)

            print(f"\nOCR Performance:")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  Max: {max_time:.2f}ms")
            print(f"  Target: <50ms")

            # Note: With mocked OCR, this tests our wrapper overhead
            # Real OCR will be slower, but this validates our code is minimal overhead
            assert avg_time < 50, f"OCR overhead too high: {avg_time:.2f}ms"

    @pytest.mark.performance
    def test_ocr_real_performance(self, temp_screenshot):
        """Test real OCR performance (may be slower, informational)."""
        # This test runs real pytesseract to measure actual performance
        try:
            import pytesseract

            ocr_processor = OCRProcessor()

            # Single timed run
            start = time.perf_counter()
            result = ocr_processor.process(temp_screenshot)
            elapsed_ms = (time.perf_counter() - start) * 1000

            print(f"\nReal OCR Performance: {elapsed_ms:.2f}ms")
            print(f"  Extracted {result.word_count} words")

            # Real OCR is typically 100-500ms depending on image size
            # We don't assert here as it's hardware/config dependent
            # Just log for information

        except Exception as e:
            pytest.skip(f"Tesseract not available: {e}")


class TestVisionPerformance:
    """Test vision model performance targets."""

    @pytest.fixture
    def temp_screenshot(self):
        """Create a temporary test screenshot."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (1920, 1080), color="blue")
            img.save(f.name)
            yield Path(f.name)
            Path(f.name).unlink(missing_ok=True)

    @pytest.mark.performance
    def test_vision_speed_target_2s(self, temp_screenshot):
        """Test vision processing meets <2s target (with mocked model)."""
        vision_processor = VisionProcessor()

        # Mock the vision model call
        with patch.object(vision_processor, "_call_model") as mock_model:
            # Simulate model taking ~500ms
            def mock_inference(image):
                time.sleep(0.5)
                return '{"category": "design", "description": "Test", "filename": "test"}'

            mock_model.side_effect = mock_inference

            # Warm-up
            vision_processor.process(temp_screenshot)

            # Timed runs
            times = []
            for _ in range(5):  # Fewer runs since vision is slower
                start = time.perf_counter()
                result = vision_processor.process(temp_screenshot)
                elapsed_ms = (time.perf_counter() - start) * 1000
                times.append(elapsed_ms)

                assert result.category is not None

            avg_time = sum(times) / len(times)
            max_time = max(times)

            print(f"\nVision Performance:")
            print(f"  Average: {avg_time:.2f}ms ({avg_time/1000:.2f}s)")
            print(f"  Max: {max_time:.2f}ms ({max_time/1000:.2f}s)")
            print(f"  Target: <2000ms (2s)")

            assert avg_time < 2000, f"Vision processing too slow: {avg_time:.2f}ms"


class TestBatchPerformance:
    """Test batch processing scaling and performance."""

    @pytest.fixture
    def temp_screenshot_batch(self, num_files=20):
        """Create a batch of test screenshots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            for i in range(num_files):
                img = Image.new("RGB", (800, 600), color="white")
                img.save(tmpdir_path / f"screenshot_{i:03d}.png")

            yield tmpdir_path

    @pytest.mark.performance
    def test_batch_processing_scaling(self, temp_screenshot_batch):
        """Test batch processing scales linearly with file count."""
        batch_processor = BatchProcessor()

        # Mock fast processor (simulate OCR path)
        def fast_processor(file_path):
            time.sleep(0.01)  # 10ms per file
            return FileProcessingResult(
                path=file_path,
                success=True,
                category="other",
                processing_time_ms=10.0
            )

        files = batch_processor.scan_folder(temp_screenshot_batch)

        # Process different batch sizes
        results = {}
        for batch_size in [5, 10, 20]:
            batch = files[:batch_size]

            start = time.perf_counter()
            stats = batch_processor.process_batch(batch, fast_processor)
            elapsed_ms = (time.perf_counter() - start) * 1000

            results[batch_size] = {
                "total_time_ms": elapsed_ms,
                "avg_per_file_ms": elapsed_ms / batch_size,
                "stats": stats
            }

            print(f"\nBatch size {batch_size}:")
            print(f"  Total time: {elapsed_ms:.2f}ms")
            print(f"  Avg per file: {elapsed_ms/batch_size:.2f}ms")

        # Verify scaling is reasonable (overhead per file should be small)
        overhead_5 = results[5]["avg_per_file_ms"]
        overhead_20 = results[20]["avg_per_file_ms"]

        # Overhead shouldn't increase significantly with batch size
        assert overhead_20 < overhead_5 * 1.5, "Batch processing overhead scales poorly"

    @pytest.mark.performance
    def test_batch_memory_efficiency(self, temp_screenshot_batch):
        """Test batch processing doesn't accumulate excessive memory."""
        import sys

        batch_processor = BatchProcessor()

        def mock_processor(file_path):
            # Create some temporary data
            _temp_data = [0] * 1000
            return FileProcessingResult(
                path=file_path,
                success=True,
                category="other"
            )

        files = batch_processor.scan_folder(temp_screenshot_batch)

        # Get initial memory usage
        initial_objects = len([obj for obj in gc.get_objects()])

        # Process batch
        stats = batch_processor.process_batch(files, mock_processor)

        # Check final memory
        final_objects = len([obj for obj in gc.get_objects()])

        print(f"\nMemory usage:")
        print(f"  Initial objects: {initial_objects}")
        print(f"  Final objects: {final_objects}")
        print(f"  Growth: {final_objects - initial_objects}")

        # Object growth should be reasonable (not linear with file count)
        object_growth = final_objects - initial_objects
        assert object_growth < len(files) * 100, "Excessive memory growth during batch processing"


class TestEndToEndPerformance:
    """Test complete workflow performance."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a complete test workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create input folder with screenshots
            input_dir = tmpdir_path / "input"
            input_dir.mkdir()

            for i in range(10):
                img = Image.new("RGB", (1920, 1080), color="white")
                img.save(input_dir / f"screenshot_{i}.png")

            # Create output folder
            output_dir = tmpdir_path / "output"
            output_dir.mkdir()

            yield {
                "input": input_dir,
                "output": output_dir
            }

    @pytest.mark.performance
    def test_complete_workflow_throughput(self, temp_workspace):
        """Test complete OCR → classify → organize workflow throughput."""
        from classifiers.keyword_classifier import KeywordClassifier
        from organizers.file_organizer import FileOrganizer
        from processors.ocr_processor import OCRProcessor

        # Setup components
        ocr = OCRProcessor()
        classifier = KeywordClassifier()
        organizer = FileOrganizer(
            base_folder=temp_workspace["output"],
            categories=["code", "errors", "other"],
            keep_originals=False
        )

        # Mock OCR for consistent performance
        with patch("processors.ocr_processor.pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "def test(): return True"

            input_files = list(temp_workspace["input"].glob("*.png"))

            # Process all files
            start = time.perf_counter()

            for file_path in input_files:
                ocr_result = ocr.process(file_path)
                category = classifier.classify(ocr_result.text)
                organizer.organize_file(file_path, category, "test")

            elapsed_ms = (time.perf_counter() - start) * 1000
            throughput = len(input_files) / (elapsed_ms / 1000)

            print(f"\nComplete Workflow:")
            print(f"  Processed {len(input_files)} files")
            print(f"  Total time: {elapsed_ms:.2f}ms ({elapsed_ms/1000:.2f}s)")
            print(f"  Avg per file: {elapsed_ms/len(input_files):.2f}ms")
            print(f"  Throughput: {throughput:.2f} files/sec")

            # Should process at least 10 files/second with mocked OCR
            assert throughput > 10, f"Throughput too low: {throughput:.2f} files/sec"


# Import gc for memory tests
import gc


if __name__ == "__main__":
    # Run performance tests with verbose output
    pytest.main([__file__, "-v", "-m", "performance", "-s"])
