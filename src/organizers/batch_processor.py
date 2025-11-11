"""Batch processor for organizing multiple screenshots efficiently."""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BatchStats:
    """Statistics from batch processing operation."""
    total_files: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    processing_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.processed == 0:
            return 0.0
        return (self.successful / self.processed) * 100


@dataclass
class FileProcessingResult:
    """Result of processing a single file."""
    path: Path
    success: bool
    category: Optional[str] = None
    error: Optional[str] = None
    processing_time_ms: float = 0.0


class BatchProcessor:
    """Handles batch processing of multiple files with progress tracking."""

    def __init__(
        self,
        supported_extensions: Optional[list[str]] = None
    ):
        """Initialize batch processor.

        Args:
            supported_extensions: List of file extensions to process (e.g., ['.png', '.jpg']).
                                If None, defaults to common image formats.
        """
        if supported_extensions is None:
            self.supported_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
        else:
            # Ensure extensions have leading dot
            self.supported_extensions = [
                ext if ext.startswith('.') else f'.{ext}'
                for ext in supported_extensions
            ]
        
        logger.info(
            f"BatchProcessor initialized with extensions: {self.supported_extensions}"
        )

    def scan_folder(
        self,
        folder_path: str | Path,
        recursive: bool = False
    ) -> list[Path]:
        """Scan folder for supported files.

        Args:
            folder_path: Path to folder to scan.
            recursive: If True, scan subdirectories recursively.

        Returns:
            List of file paths matching supported extensions.
        """
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            logger.error(f"Folder not found: {folder_path}")
            return []
        
        if not folder_path.is_dir():
            logger.error(f"Not a directory: {folder_path}")
            return []
        
        files = []
        pattern = "**/*" if recursive else "*"
        
        try:
            for item in folder_path.glob(pattern):
                if item.is_file() and item.suffix.lower() in self.supported_extensions:
                    files.append(item)
            
            logger.info(
                f"Found {len(files)} supported files in {folder_path} "
                f"(recursive={recursive})"
            )
            return files
            
        except Exception as e:
            logger.error(f"Error scanning folder {folder_path}: {e}")
            return []

    def process_batch(
        self,
        files: list[Path],
        processor_func: Callable[[Path], FileProcessingResult],
        progress_callback: Optional[Callable[[int, int, Path], None]] = None
    ) -> BatchStats:
        """Process a batch of files with progress tracking.

        Args:
            files: List of file paths to process.
            processor_func: Function to process each file. Should return FileProcessingResult.
            progress_callback: Optional callback function(current, total, file_path) for progress updates.

        Returns:
            BatchStats with processing results and statistics.
        """
        stats = BatchStats(total_files=len(files))
        start_time = time.perf_counter()
        
        logger.info(f"Starting batch processing of {len(files)} files")
        
        for idx, file_path in enumerate(files, 1):
            try:
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(idx, len(files), file_path)
                
                # Process file
                result = processor_func(file_path)
                stats.processed += 1
                
                if result.success:
                    stats.successful += 1
                    logger.debug(
                        f"[{idx}/{len(files)}] Successfully processed: {file_path.name} -> {result.category}"
                    )
                else:
                    stats.failed += 1
                    error_msg = f"{file_path.name}: {result.error or 'Unknown error'}"
                    stats.errors.append(error_msg)
                    logger.warning(
                        f"[{idx}/{len(files)}] Failed to process: {error_msg}"
                    )
                    
            except Exception as e:
                stats.failed += 1
                error_msg = f"{file_path.name}: {str(e)}"
                stats.errors.append(error_msg)
                logger.error(
                    f"[{idx}/{len(files)}] Exception processing {file_path.name}: {e}"
                )
        
        stats.processing_time_ms = (time.perf_counter() - start_time) * 1000
        
        logger.info(
            f"Batch processing complete: {stats.successful}/{stats.total_files} successful "
            f"({stats.success_rate:.1f}% success rate) in {stats.processing_time_ms:.2f}ms"
        )
        
        if stats.errors:
            logger.warning(f"Encountered {len(stats.errors)} errors during batch processing")
        
        return stats

    def process_folder(
        self,
        folder_path: str | Path,
        processor_func: Callable[[Path], FileProcessingResult],
        recursive: bool = False,
        progress_callback: Optional[Callable[[int, int, Path], None]] = None
    ) -> BatchStats:
        """Scan and process all supported files in a folder.

        Args:
            folder_path: Path to folder to process.
            processor_func: Function to process each file.
            recursive: If True, process subdirectories recursively.
            progress_callback: Optional progress callback function.

        Returns:
            BatchStats with processing results.
        """
        # Scan folder for files
        files = self.scan_folder(folder_path, recursive=recursive)
        
        if not files:
            logger.warning(f"No supported files found in {folder_path}")
            return BatchStats(total_files=0)
        
        # Process batch
        return self.process_batch(files, processor_func, progress_callback)

    def filter_files_by_size(
        self,
        files: list[Path],
        min_size_kb: Optional[int] = None,
        max_size_kb: Optional[int] = None
    ) -> list[Path]:
        """Filter files by size constraints.

        Args:
            files: List of file paths to filter.
            min_size_kb: Minimum file size in KB (inclusive).
            max_size_kb: Maximum file size in KB (inclusive).

        Returns:
            Filtered list of file paths.
        """
        filtered = []
        
        for file_path in files:
            try:
                size_kb = file_path.stat().st_size / 1024
                
                if min_size_kb is not None and size_kb < min_size_kb:
                    logger.debug(f"Skipping {file_path.name}: too small ({size_kb:.1f}KB)")
                    continue
                
                if max_size_kb is not None and size_kb > max_size_kb:
                    logger.debug(f"Skipping {file_path.name}: too large ({size_kb:.1f}KB)")
                    continue
                
                filtered.append(file_path)
                
            except Exception as e:
                logger.warning(f"Error checking size of {file_path}: {e}")
        
        logger.info(f"Filtered {len(files)} files to {len(filtered)} based on size constraints")
        return filtered

    def get_summary_report(self, stats: BatchStats) -> str:
        """Generate a human-readable summary report.

        Args:
            stats: BatchStats to summarize.

        Returns:
            Formatted summary string.
        """
        report_lines = [
            "=== Batch Processing Summary ===",
            f"Total Files: {stats.total_files}",
            f"Processed: {stats.processed}",
            f"Successful: {stats.successful}",
            f"Failed: {stats.failed}",
            f"Skipped: {stats.skipped}",
            f"Success Rate: {stats.success_rate:.1f}%",
            f"Processing Time: {stats.processing_time_ms:.2f}ms",
            f"Avg Time/File: {stats.processing_time_ms / stats.processed:.2f}ms" if stats.processed > 0 else "Avg Time/File: N/A",
        ]
        
        if stats.errors:
            report_lines.append(f"\n=== Errors ({len(stats.errors)}) ===")
            for idx, error in enumerate(stats.errors[:10], 1):  # Show first 10 errors
                report_lines.append(f"{idx}. {error}")
            if len(stats.errors) > 10:
                report_lines.append(f"... and {len(stats.errors) - 10} more errors")
        
        return "\n".join(report_lines)
