"""File organizer for screenshot management with safe file operations."""

import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OrganizeResult:
    """Result of a file organization operation."""
    success: bool
    original_path: Path
    destination_path: Optional[Path]
    error: Optional[str] = None
    archived: bool = False


class FileOrganizer:
    """Manages file organization with category-based folder structure."""

    def __init__(
        self,
        base_folder: str | Path,
        categories: list[str],
        keep_originals: bool = True
    ):
        """Initialize file organizer.

        Args:
            base_folder: Base directory for organized screenshots.
            categories: List of valid category names for folders.
            keep_originals: If True, copy files instead of moving them.
        """
        self.base_folder = Path(base_folder).expanduser()
        self.categories = categories
        self.keep_originals = keep_originals
        self.archive_folder = self.base_folder / "_originals"
        
        logger.info(
            f"FileOrganizer initialized: base={self.base_folder}, "
            f"categories={categories}, keep_originals={keep_originals}"
        )

    def ensure_folder_structure(self):
        """Create base folder and category subfolders if they don't exist."""
        try:
            # Create base folder
            self.base_folder.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured base folder exists: {self.base_folder}")
            
            # Create category folders
            for category in self.categories:
                category_path = self.base_folder / category
                category_path.mkdir(exist_ok=True)
                logger.debug(f"Ensured category folder exists: {category_path}")
            
            # Create archive folder if keeping originals
            if self.keep_originals:
                self.archive_folder.mkdir(exist_ok=True)
                logger.debug(f"Ensured archive folder exists: {self.archive_folder}")
                
        except Exception as e:
            logger.error(f"Failed to create folder structure: {e}")
            raise

    def generate_safe_filename(
        self,
        suggested_name: str,
        category: str,
        original_extension: str
    ) -> str:
        """Generate a safe, unique filename.

        Args:
            suggested_name: Suggested base filename (will be sanitized).
            category: Category for the file.
            original_extension: Original file extension (e.g., '.png').

        Returns:
            Safe filename with timestamp and extension.
        """
        # Sanitize suggested name: remove special chars, limit length
        safe_name = re.sub(r'[^\w\s-]', '', suggested_name)
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        safe_name = safe_name.strip('_').lower()
        
        # Limit length to reasonable size
        if len(safe_name) > 50:
            safe_name = safe_name[:50]
        
        # Fallback if sanitization removed everything
        if not safe_name:
            safe_name = "screenshot"
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure extension has leading dot
        if not original_extension.startswith('.'):
            original_extension = f'.{original_extension}'
        
        filename = f"{safe_name}_{timestamp}{original_extension}"
        
        logger.debug(f"Generated safe filename: {filename} from '{suggested_name}'")
        return filename

    def get_unique_path(self, target_path: Path) -> Path:
        """Get unique path by adding counter if file exists.

        Args:
            target_path: Desired file path.

        Returns:
            Unique path (may have counter appended if original exists).
        """
        if not target_path.exists():
            return target_path
        
        # File exists, add counter
        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent
        
        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                logger.debug(f"Resolved conflict: {target_path} -> {new_path}")
                return new_path
            counter += 1

    def organize_file(
        self,
        source_path: str | Path,
        category: str,
        suggested_filename: Optional[str] = None
    ) -> OrganizeResult:
        """Organize a file into the appropriate category folder.

        Args:
            source_path: Path to the file to organize.
            category: Category to organize into (must be in self.categories).
            suggested_filename: Optional suggested base filename.

        Returns:
            OrganizeResult with operation details.
        """
        source_path = Path(source_path)
        
        # Validate source file
        if not source_path.exists():
            error = f"Source file not found: {source_path}"
            logger.error(error)
            return OrganizeResult(
                success=False,
                original_path=source_path,
                destination_path=None,
                error=error
            )
        
        # Validate category
        if category not in self.categories:
            logger.warning(
                f"Invalid category '{category}', defaulting to 'other'"
            )
            category = "other" if "other" in self.categories else self.categories[0]
        
        try:
            # Ensure folder structure exists
            self.ensure_folder_structure()
            
            # Generate safe filename
            if suggested_filename:
                filename = self.generate_safe_filename(
                    suggested_filename,
                    category,
                    source_path.suffix
                )
            else:
                # Use original filename with timestamp
                filename = self.generate_safe_filename(
                    source_path.stem,
                    category,
                    source_path.suffix
                )
            
            # Determine destination path
            destination_folder = self.base_folder / category
            destination_path = destination_folder / filename
            
            # Handle filename conflicts
            destination_path = self.get_unique_path(destination_path)
            
            # Archive original if keeping originals
            archived = False
            if self.keep_originals:
                archive_path = self.archive_folder / source_path.name
                archive_path = self.get_unique_path(archive_path)
                shutil.copy2(source_path, archive_path)
                archived = True
                logger.debug(f"Archived original to: {archive_path}")
            
            # Move or copy file
            if self.keep_originals:
                shutil.copy2(source_path, destination_path)
                operation = "copied"
            else:
                shutil.move(str(source_path), str(destination_path))
                operation = "moved"
            
            logger.info(
                f"Successfully {operation} {source_path.name} to "
                f"{category}/{destination_path.name}"
            )
            
            return OrganizeResult(
                success=True,
                original_path=source_path,
                destination_path=destination_path,
                archived=archived
            )
            
        except Exception as e:
            error = f"Failed to organize file: {e}"
            logger.error(error)
            return OrganizeResult(
                success=False,
                original_path=source_path,
                destination_path=None,
                error=error
            )

    def get_category_path(self, category: str) -> Path:
        """Get the path for a specific category folder.

        Args:
            category: Category name.

        Returns:
            Path to category folder.
        """
        return self.base_folder / category

    def get_statistics(self) -> dict[str, int]:
        """Get statistics about organized files.

        Returns:
            Dictionary with counts per category.
        """
        stats = {}
        
        try:
            for category in self.categories:
                category_path = self.base_folder / category
                if category_path.exists():
                    files = list(category_path.glob('*'))
                    stats[category] = len([f for f in files if f.is_file()])
                else:
                    stats[category] = 0
                    
            logger.debug(f"Organization statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to gather statistics: {e}")
            return {}
