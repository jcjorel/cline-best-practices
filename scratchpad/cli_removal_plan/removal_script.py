#!/usr/bin/env python3
"""
Legacy CLI Removal Script

This script implements the removal of legacy CLI files after verification has confirmed
it's safe to proceed. It handles creating a backup branch, removing files in the correct
order, and summarizing the removal operation.

Usage:
    python removal_script.py [--verification-report REPORT] [--dry-run] [--force]

Options:
    --verification-report REPORT   Path to the verification report [default: latest report]
    --dry-run                      Show what would be done, but don't actually remove files
    --force                        Remove files even if verification report recommends against it
"""

import os
import re
import sys
import glob
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Files to remove, in removal order
REMOVAL_ORDER = [
    # Test files first
    "src/dbp_cli/commands/test/",
    
    # Command implementation files
    "src/dbp_cli/commands/commit.py",
    "src/dbp_cli/commands/config.py",
    "src/dbp_cli/commands/query.py",
    "src/dbp_cli/commands/server.py",
    "src/dbp_cli/commands/status.py",
    "src/dbp_cli/commands/hstc.py",
    "src/dbp_cli/commands/modeldiscovery.py",
    
    # Command structure files
    "src/dbp_cli/commands/base.py",
    "src/dbp_cli/commands/click_adapter.py",
    "src/dbp_cli/commands/__init__.py",
    
    # Core CLI files last
    "src/dbp_cli/cli.py",
    "src/dbp_cli/__main__.py",
]

# Special files to preserve/move if needed
SPECIAL_FILES = {
    "src/dbp_cli/commands/HSTC.md": "src/dbp_cli/cli_click/commands/HSTC.md",  # Move to new location
}

def find_latest_verification_report():
    """
    Find the most recent verification report.
    
    Returns:
        Path: Path to the most recent report, or None if not found
    """
    pattern = "scratchpad/cli_removal_plan/cli_removal_verification_*.md"
    reports = glob.glob(pattern)
    if not reports:
        return None
    
    # Sort by modification time, newest first
    reports.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return Path(reports[0])

def parse_verification_report(report_path):
    """
    Parse a verification report to determine if it's safe to proceed.
    
    Args:
        report_path (Path): Path to the verification report
        
    Returns:
        dict: Report summary and safety status
    """
    if not report_path.exists():
        return {
            "found": False,
            "safe": False,
            "message": f"Report not found: {report_path}",
            "references": 0,
            "entry_points_updated": False,
            "missing_commands": []
        }
    
    try:
        content = report_path.read_text(encoding='utf-8')
        
        # Extract references count
        references_match = re.search(r'Files with references to legacy CLI: (\d+)', content)
        references = int(references_match.group(1)) if references_match else -1
        
        # Check if entry points are updated
        entry_points_match = re.search(r'Entry points updated: (Yes|No)', content)
        entry_points_updated = entry_points_match.group(1) == "Yes" if entry_points_match else False
        
        # Extract missing commands
        missing_commands = []
        in_missing_section = False
        for line in content.splitlines():
            if line == "### Missing Commands":
                in_missing_section = True
                continue
            elif in_missing_section and line.startswith("###"):
                in_missing_section = False
                continue
            
            if in_missing_section and line.startswith("- "):
                missing_commands.append(line[2:])
            elif in_missing_section and "All commands have been migrated" in line:
                break
        
        # Check if it's safe to proceed
        safe_match = re.search(r'✅ \*\*Safe to proceed with removal\*\*', content)
        safe = safe_match is not None
        
        if safe:
            message = "Verification passed. Safe to proceed with removal."
        elif references > 0:
            message = f"Verification failed. Found {references} files with references to legacy CLI."
        elif not entry_points_updated:
            message = "Verification failed. Entry points not updated in setup.py."
        elif missing_commands:
            message = f"Verification failed. Found {len(missing_commands)} missing commands."
        else:
            message = "Verification failed for unknown reasons."
        
        return {
            "found": True,
            "safe": safe,
            "message": message,
            "references": references,
            "entry_points_updated": entry_points_updated,
            "missing_commands": missing_commands
        }
    except Exception as e:
        return {
            "found": False,
            "safe": False,
            "message": f"Error parsing report: {e}",
            "references": -1,
            "entry_points_updated": False,
            "missing_commands": []
        }

def create_backup_branch():
    """
    Create a backup branch before removal.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if we're in a git repository
        subprocess.check_call(["git", "rev-parse", "--is-inside-work-tree"], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Create backup branch
        branch_name = f"backup/pre-cli-removal-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        subprocess.check_call(["git", "checkout", "-b", branch_name])
        
        # Commit changes
        subprocess.check_call(["git", "add", "."])
        subprocess.check_call(["git", "commit", "-m", "State before legacy CLI removal"])
        
        # Create and switch to new feature branch
        subprocess.check_call(["git", "checkout", "-b", "feature/remove-legacy-cli"])
        
        print(f"Created backup branch: {branch_name}")
        print("Switched to branch: feature/remove-legacy-cli")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating backup branch: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def remove_files(dry_run=False):
    """
    Remove legacy CLI files in the correct order.
    
    Args:
        dry_run (bool): If True, only show what would be done
        
    Returns:
        tuple: (removed_files, failed_files)
    """
    removed_files = []
    failed_files = []
    
    # First, handle special files (preserve/move)
    for src, dst in SPECIAL_FILES.items():
        src_path = Path(src)
        if not src_path.exists():
            print(f"Special file not found, skipping: {src}")
            continue
            
        if dst:  # Move file to new location
            dst_path = Path(dst)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            if dry_run:
                print(f"Would move: {src} -> {dst}")
            else:
                try:
                    dst_path.write_text(src_path.read_text(encoding='utf-8'))
                    print(f"Moved: {src} -> {dst}")
                    src_path.unlink()
                    removed_files.append(src)
                except Exception as e:
                    print(f"Error moving {src}: {e}")
                    failed_files.append(src)
    
    # Then remove files in specified order
    for file_path in REMOVAL_ORDER:
        path = Path(file_path)
        
        if not path.exists():
            print(f"File not found, skipping: {file_path}")
            continue
            
        if dry_run:
            print(f"Would remove: {file_path}")
        else:
            try:
                if path.is_dir():
                    # Remove directory and all contents
                    import shutil
                    shutil.rmtree(path)
                    print(f"Removed directory: {file_path}")
                else:
                    # Remove single file
                    path.unlink()
                    print(f"Removed file: {file_path}")
                
                removed_files.append(file_path)
            except Exception as e:
                print(f"Error removing {file_path}: {e}")
                failed_files.append(file_path)
    
    # Clean up empty directories
    for dir_path in ["src/dbp_cli/commands"]:
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            # Check if directory is empty
            if not list(path.iterdir()):
                if dry_run:
                    print(f"Would remove empty directory: {dir_path}")
                else:
                    try:
                        path.rmdir()
                        print(f"Removed empty directory: {dir_path}")
                    except Exception as e:
                        print(f"Error removing directory {dir_path}: {e}")
    
    return removed_files, failed_files

def main():
    parser = argparse.ArgumentParser(description="Remove legacy CLI files")
    parser.add_argument('--verification-report', help='Path to verification report')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without removing files')
    parser.add_argument('--force', action='store_true', help='Force removal even if verification fails')
    args = parser.parse_args()
    
    # Find verification report
    if args.verification_report:
        report_path = Path(args.verification_report)
    else:
        report_path = find_latest_verification_report()
        if not report_path:
            print("No verification report found. Run verification_script.py first.")
            print("or specify a report with --verification-report.")
            return 1
    
    # Parse verification report
    report_summary = parse_verification_report(report_path)
    print(f"Verification report: {report_path}")
    print(f"Status: {report_summary['message']}")
    
    # Check if it's safe to proceed
    if not report_summary['safe'] and not args.force:
        print("\nVerification failed. Not safe to proceed with removal.")
        print("Run with --force to override this check.")
        return 1
    
    if not report_summary['safe'] and args.force:
        print("\n⚠️ WARNING: Proceeding with removal despite verification failure.")
        print("This may break functionality. Make sure you have a backup.")
    
    # Create backup branch if not in dry run mode
    if not args.dry_run:
        print("\nCreating backup branch...")
        success = create_backup_branch()
        if not success and not args.force:
            print("Failed to create backup branch. Use --force to continue anyway.")
            return 1
        elif not success:
            print("Failed to create backup branch. Continuing due to --force.")
    
    # Remove files
    print("\nRemoving legacy CLI files...")
    removed_files, failed_files = remove_files(args.dry_run)
    
    # Print summary
    print("\nSummary:")
    print(f"- {'Would remove' if args.dry_run else 'Removed'}: {len(removed_files)} files")
    print(f"- Failed: {len(failed_files)} files")
    
    if failed_files:
        print("\nFailed to remove the following files:")
        for file_path in failed_files:
            print(f"- {file_path}")
    
    if args.dry_run:
        print("\nThis was a dry run. No files were actually removed.")
        print("Run without --dry-run to perform the removal.")
    
    return 0 if not failed_files else 1

if __name__ == "__main__":
    sys.exit(main())
