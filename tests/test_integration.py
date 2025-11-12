"""Integration tests for end-to-end screenshot processing workflows."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PIL import Image

from classifiers.keyword_classifier import KeywordClassifier
from mcp_tools import MCPToolHandlers
from organizers.batch_processor import BatchProcessor, FileProcessingResult
from organizers.file_organizer import FileOrganizer
from processors.ocr_processor import OCRProcessor, OCRResult
from processors.vision_processor import VisionProcessor, VisionResult


class TestOCRWorkflow:
    """Test complete OCR-based processing workflow."""

    @pytest.fixture
    def temp_screenshot(self):
        """Create a temporary test screenshot."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Create a simple test image
            img = Image.new("RGB", (800, 600), color="white")
            img.save(f.name)
            yield Path(f.name)
            Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_ocr_to_classification_workflow(self, temp_screenshot):
        """Test OCR extraction followed by keyword classification."""
        # Mock OCR to return code-like text
        with patch("processors.ocr_processor.pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "def hello_world():\n    print('Hello, World!')\n    return True"

            # Process with OCR
            ocr_processor = OCRProcessor(min_words_threshold=5)
            ocr_result = ocr_processor.process(temp_screenshot)

            # Verify OCR results
            assert ocr_result.sufficient_text is True
            assert ocr_result.word_count >= 5
            assert "def" in ocr_result.text.lower()

            # Classify the text
            classifier = KeywordClassifier()
            category = classifier.classify(ocr_result.text)

            # Should classify as code
            assert category == "code"

    def test_ocr_to_organization_workflow(self, temp_screenshot, temp_output_dir):
        """Test complete OCR → classification → organization workflow."""
        with patch("processors.ocr_processor.pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "Error: NullPointerException at line 42"

            # Setup components
            ocr_processor = OCRProcessor(min_words_threshold=3)
            classifier = KeywordClassifier()
            organizer = FileOrganizer(
                base_folder=temp_output_dir,
                categories=["code", "errors", "documentation", "other"],
                keep_originals=False
            )

            # Process
            ocr_result = ocr_processor.process(temp_screenshot)
            category = classifier.classify(ocr_result.text)
            organize_result = organizer.organize_file(
                temp_screenshot,
                category,
                "error_screenshot"
            )

            # Verify workflow
            assert category == "errors"
            assert organize_result.success is True
            assert organize_result.destination_path.parent.name == "errors"
            assert organize_result.destination_path.exists()

    def test_insufficient_text_fallback(self, temp_screenshot):
        """Test fallback to vision when OCR finds insufficient text."""
        with patch("processors.ocr_processor.pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "Hi"  # Only 1 word

            ocr_processor = OCRProcessor(min_words_threshold=10)
            ocr_result = ocr_processor.process(temp_screenshot)

            # Should indicate insufficient text
            assert ocr_result.sufficient_text is False
            assert ocr_result.word_count < 10


class TestVisionWorkflow:
    """Test vision model-based processing workflow."""

    @pytest.fixture
    def temp_screenshot(self):
        """Create a temporary test screenshot."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (800, 600), color="blue")
            img.save(f.name)
            yield Path(f.name)
            Path(f.name).unlink(missing_ok=True)

    def test_vision_processing_workflow(self, temp_screenshot):
        """Test vision model processing and response parsing."""
        vision_processor = VisionProcessor()

        # Mock both model loading and model call to avoid ImportError
        vision_processor.model = Mock()  # Pretend model is loaded
        
        # Mock the model call to return a valid JSON response
        with patch.object(vision_processor, "_call_model") as mock_model:
            mock_model.return_value = '{"category": "design", "description": "Blue color palette", "filename": "blue_palette"}'

            result = vision_processor.process(temp_screenshot)

            # Verify results
            assert isinstance(result, VisionResult)
            assert result.category == "design"
            assert result.description == "Blue color palette"
            assert result.suggested_filename == "blue_palette"
            assert result.processing_time_ms > 0

    def test_vision_invalid_category_fallback(self, temp_screenshot):
        """Test vision processor handles invalid categories gracefully."""
        vision_processor = VisionProcessor()
        
        # Mock model loading to avoid ImportError
        vision_processor.model = Mock()

        with patch.object(vision_processor, "_call_model") as mock_model:
            mock_model.return_value = '{"category": "invalid_cat", "description": "Test", "filename": "test"}'

            result = vision_processor.process(temp_screenshot)

            # Should default to "other" for invalid category
            assert result.category == "other"


class TestBatchProcessing:
    """Test batch processing workflows."""

    @pytest.fixture
    def temp_screenshot_folder(self):
        """Create a folder with multiple test screenshots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create multiple test images
            for i in range(3):
                img = Image.new("RGB", (100, 100), color="white")
                img.save(tmpdir_path / f"screenshot_{i}.png")

            yield tmpdir_path

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_batch_folder_scanning(self, temp_screenshot_folder):
        """Test scanning folder for supported files."""
        batch_processor = BatchProcessor(supported_extensions=[".png", ".jpg"])

        files = batch_processor.scan_folder(temp_screenshot_folder, recursive=False)

        assert len(files) == 3
        assert all(f.suffix == ".png" for f in files)

    def test_batch_processing_with_progress(self, temp_screenshot_folder):
        """Test batch processing with progress tracking."""
        batch_processor = BatchProcessor()

        # Track progress callback calls
        progress_calls = []

        def progress_callback(current, total, file_path):
            progress_calls.append((current, total, file_path))

        # Mock processor function
        def mock_processor(file_path):
            return FileProcessingResult(
                path=file_path,
                success=True,
                category="other",
                processing_time_ms=10.0
            )

        files = batch_processor.scan_folder(temp_screenshot_folder)
        stats = batch_processor.process_batch(
            files,
            mock_processor,
            progress_callback=progress_callback
        )

        # Verify progress tracking
        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3, files[0])
        assert progress_calls[-1] == (3, 3, files[-1])

        # Verify stats
        assert stats.total_files == 3
        assert stats.successful == 3
        assert stats.failed == 0
        assert stats.success_rate == 100.0

    def test_batch_processing_with_failures(self, temp_screenshot_folder):
        """Test batch processing handles individual file failures."""
        batch_processor = BatchProcessor()

        # Mock processor that fails on second file
        call_count = [0]

        def failing_processor(file_path):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Simulated processing error")
            return FileProcessingResult(
                path=file_path,
                success=True,
                category="other"
            )

        files = batch_processor.scan_folder(temp_screenshot_folder)
        stats = batch_processor.process_batch(files, failing_processor)

        # Should continue despite failure
        assert stats.total_files == 3
        assert stats.successful == 2
        assert stats.failed == 1
        assert len(stats.errors) == 1
        assert "Simulated processing error" in stats.errors[0]


class TestMCPToolHandlers:
    """Test MCP tool handlers end-to-end."""

    @pytest.fixture
    def temp_screenshot(self):
        """Create a temporary test screenshot."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (800, 600), color="white")
            img.save(f.name)
            yield Path(f.name)
            Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_analyze_screenshot_with_ocr(self, temp_screenshot):
        """Test analyze_screenshot tool with OCR path."""
        with patch("processors.ocr_processor.pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "import numpy as np\nimport pandas as pd\ndata = pd.read_csv('file.csv')"

            handlers = MCPToolHandlers()
            result = handlers.analyze_screenshot(str(temp_screenshot), force_vision=False)

            # Verify response structure
            assert "category" in result
            assert "suggested_filename" in result
            assert "processing_method" in result
            assert "processing_time_ms" in result

            # Should use OCR method
            assert result["processing_method"] == "ocr"
            assert result["category"] == "code"
            assert result["extracted_text"] is not None

    def test_analyze_screenshot_force_vision(self, temp_screenshot):
        """Test analyze_screenshot tool with force_vision=True."""
        handlers = MCPToolHandlers()
        
        # Mock model loading to avoid ImportError
        handlers.vision_processor.model = Mock()

        with patch.object(handlers.vision_processor, "_call_model") as mock_model:
            mock_model.return_value = '{"category": "memes", "description": "Funny cat picture", "filename": "funny_cat"}'

            result = handlers.analyze_screenshot(str(temp_screenshot), force_vision=True)

            # Should use vision method
            assert result["processing_method"] == "vision"
            assert result["category"] == "memes"
            assert result["extracted_text"] is None

    def test_batch_process_tool(self, temp_output_dir):
        """Test batch_process tool end-to-end."""
        # Create test folder with screenshots
        test_folder = temp_output_dir / "input"
        test_folder.mkdir()

        for i in range(2):
            img = Image.new("RGB", (100, 100), color="white")
            img.save(test_folder / f"test_{i}.png")

        # Mock OCR with enough text to exceed min_words threshold
        with patch("processors.ocr_processor.pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "Error 404: Page not found. The requested resource could not be located on the server."

            config = {
                "ocr_min_words": 3,
                "organization": {
                    "base_folder": str(temp_output_dir / "organized"),
                    "categories": ["code", "errors", "other"],
                    "keep_originals": False
                }
            }
            handlers = MCPToolHandlers(config)

            result = handlers.batch_process(
                folder=str(test_folder),
                recursive=False,
                organize=True
            )

            # Verify batch processing results
            assert result["total_files"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0
            assert "categories_count" in result
            assert result["categories_count"]["errors"] == 2

    def test_organize_file_tool(self, temp_screenshot, temp_output_dir):
        """Test organize_file tool."""
        config = {
            "organization": {
                "base_folder": str(temp_output_dir),
                "categories": ["code", "errors", "other"],
                "keep_originals": False
            }
        }
        handlers = MCPToolHandlers(config)

        result = handlers.organize_file(
            source_path=str(temp_screenshot),
            category="code",
            new_filename="test_code_file",
            archive_original=False,
            base_path=str(temp_output_dir)
        )

        # Verify organization
        assert result["success"] is True
        assert result["destination_path"] is not None
        assert "code" in result["destination_path"]
        assert Path(result["destination_path"]).exists()


class TestErrorScenarios:
    """Test error handling and edge cases."""

    def test_nonexistent_file(self):
        """Test handling of nonexistent file."""
        ocr_processor = OCRProcessor()

        with pytest.raises(FileNotFoundError):
            ocr_processor.process("/nonexistent/path/to/file.png")

    def test_invalid_image_file(self):
        """Test handling of invalid/corrupted image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Write invalid data
            f.write(b"not a real image")
            temp_path = Path(f.name)

        try:
            ocr_processor = OCRProcessor()
            with pytest.raises(Exception):  # Should raise some kind of error
                ocr_processor.process(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_invalid_category_defaults_to_other(self):
        """Test that invalid categories default to 'other'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test file
            test_file = tmpdir_path / "test.png"
            img = Image.new("RGB", (100, 100), color="white")
            img.save(test_file)

            organizer = FileOrganizer(
                base_folder=tmpdir_path / "organized",
                categories=["code", "errors", "other"],
                keep_originals=False
            )

            # Try to organize with invalid category
            result = organizer.organize_file(
                test_file,
                category="invalid_category_name",
                suggested_filename="test"
            )

            # Should succeed with fallback to 'other'
            assert result.success is True

    def test_mcp_tool_missing_file_error(self):
        """Test MCP tool handlers return proper error for missing files."""
        handlers = MCPToolHandlers()

        with pytest.raises(FileNotFoundError):
            handlers.analyze_screenshot("/path/that/does/not/exist.png")

    def test_batch_process_empty_folder(self):
        """Test batch processing handles empty folders gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handlers = MCPToolHandlers()

            result = handlers.batch_process(folder=tmpdir, organize=False)

            # Should return zero results
            assert result["total_files"] == 0
            assert result["successful"] == 0
            assert result["failed"] == 0
