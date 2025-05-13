#!/usr/bin/env python3
"""
Legacy CLI Removal Verification Script

This script analyzes the codebase to identify dependencies on the legacy CLI
implementation and generates a report to help safely remove obsolete files.

Usage:
    python verification_script.py [--output-dir OUTPUT_DIR]

Options:
    --output-dir OUTPUT_DIR  Directory to save the verification report [default: ./]
"""

import os
import re
import sys
import argparse
import importlib
import subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Files to check for removal
LEGACY_FILES = [
    "src/dbp_cli/cli.py",
    "src/dbp_cli/__main__.py",
    "src/dbp_cli/commands/base.py",
    "src/dbp_cli/commands/click_adapter.py",
    "src/dbp_cli/commands/commit.py",
    "src/dbp_cli/commands/config.py",
    "src/dbp_cli/commands/query.py",
    "src/dbp_cli/commands/server.py",
    "src/dbp_cli/commands/status.py",
    "src/dbp_cli/commands/hstc.py",
    "src/dbp_cli/commands/modeldiscovery.py",
    "src/dbp_cli/commands/__init__.py",
]

# Directories to scan for references
SCAN_DIRS = [
    "src/dbp_cli",
    "src/dbp",
    "scripts",
]

class LegacyCLIAnalyzer:
    """
    Analyzes the codebase to identify dependencies on the legacy CLI implementation.
    """
    
    def __init__(self, project_root="."):
        """
        Initialize the analyzer with the project root directory.
        
        Args:
            project_root (str): Path to the project root directory
        """
        self.project_root = Path(project_root).resolve()
        self.references = defaultdict(list)
        self.import_patterns = [
            re.compile(r'from\s+dbp_cli\.cli\s+import'),
            re.compile(r'import\s+dbp_cli\.cli'),
            re.compile(r'from\s+dbp_cli\.commands\s+import'),
            re.compile(r'import\s+dbp_cli\.commands'),
            re.compile(r'from\s+dbp_cli\.commands\.\w+\s+import'),
        ]
        
    def scan_file(self, file_path):
        """
        Scan a single file for references to the legacy CLI.
        
        Args:
            file_path (Path): Path to the file to scan
        """
        if not file_path.exists() or not file_path.is_file():
            return
        
        if file_path.suffix not in ['.py', '.sh', '.bash']:
            return
            
        try:
            content = file_path.read_text(encoding='utf-8')
            for pattern in self.import_patterns:
                matches = pattern.findall(content)
                for match in matches:
                    self.references[str(file_path)].append(match)
                    
            # Check for direct file references
            for legacy_file in LEGACY_FILES:
                file_name = Path(legacy_file).name
                if file_name in content:
                    self.references[str(file_path)].append(f"Direct reference to {file_name}")
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
    
    def scan_directory(self, dir_path):
        """
        Recursively scan a directory for references to the legacy CLI.
        
        Args:
            dir_path (str): Path to the directory to scan
        """
        dir_path = Path(dir_path)
        if not dir_path.exists() or not dir_path.is_dir():
            return
            
        for path in dir_path.glob('**/*'):
            if path.is_file():
                self.scan_file(path)
    
    def analyze(self):
        """
        Analyze the codebase for references to the legacy CLI.
        """
        for dir_path in SCAN_DIRS:
            abs_path = self.project_root / dir_path
            self.scan_directory(abs_path)
        
        return self.references
        
    def check_entry_points(self):
        """
        Check if setup.py has been updated to use the new CLI implementation.
        
        Returns:
            tuple: (is_updated, entry_point_text)
        """
        setup_py = self.project_root / 'setup.py'
        if not setup_py.exists():
            return False, "setup.py not found"
            
        try:
            content = setup_py.read_text(encoding='utf-8')
            entry_points_match = re.search(r'entry_points\s*=\s*{([^}]+)}', content, re.DOTALL)
            if not entry_points_match:
                return False, "No entry_points found in setup.py"
                
            entry_points_text = entry_points_match.group(1)
            
            # Check if entry points reference the new CLI
            if 'cli_click' in entry_points_text:
                return True, entry_points_text.strip()
            else:
                return False, entry_points_text.strip()
        except Exception as e:
            return False, f"Error reading setup.py: {e}"
            
    def compare_commands(self):
        """
        Compare commands in old and new implementations.
        
        Returns:
            dict: Command comparison results
        """
        results = {
            'old_commands': [],
            'new_commands': [],
            'missing': [],
            'migrated': []
        }
        
        # Find old command handlers
        try:
            cmd = f"grep -r 'class.*CommandHandler' --include='*.py' {self.project_root}/src/dbp_cli/commands/"
            output = subprocess.check_output(cmd, shell=True, text=True)
            old_commands = []
            for line in output.splitlines():
                match = re.search(r'class\s+(\w+)CommandHandler', line)
                if match:
                    old_commands.append(match.group(1).lower())
            results['old_commands'] = sorted(old_commands)
        except Exception as e:
            results['old_commands'] = [f"Error: {e}"]
            
        # Find new click commands
        try:
            cmd = f"grep -r '@click\\.command\\|@click\\.group' --include='*.py' {self.project_root}/src/dbp_cli/cli_click/"
            output = subprocess.check_output(cmd, shell=True, text=True)
            new_commands = []
            for line in output.splitlines():
                match = re.search(r'def\s+(\w+)\(', line)
                if match:
                    new_commands.append(match.group(1).lower())
            results['new_commands'] = sorted(new_commands)
        except Exception as e:
            results['new_commands'] = [f"Error: {e}"]
            
        # Compare commands
        if isinstance(results['old_commands'], list) and isinstance(results['new_commands'], list):
            results['missing'] = [cmd for cmd in results['old_commands'] 
                                 if not any(cmd in new_cmd for new_cmd in results['new_commands'])]
            results['migrated'] = [cmd for cmd in results['old_commands'] 
                                  if any(cmd in new_cmd for new_cmd in results['new_commands'])]
            
        return results

def generate_report(analyzer, output_dir):
    """
    Generate a verification report.
    
    Args:
        analyzer (LegacyCLIAnalyzer): The analyzer instance
        output_dir (str): Directory to save the report
    """
    references = analyzer.analyze()
    entry_points_updated, entry_points_text = analyzer.check_entry_points()
    command_comparison = analyzer.compare_commands()
    
    # Create report directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    report_file = output_path / f"cli_removal_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Legacy CLI Removal Verification Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # File reference analysis
        f.write("## References to Legacy CLI\n\n")
        if not references:
            f.write("No references found to the legacy CLI implementation.\n\n")
        else:
            f.write("The following files contain references to the legacy CLI:\n\n")
            for file_path, refs in references.items():
                f.write(f"### {file_path}\n\n")
                for ref in refs:
                    f.write(f"- `{ref}`\n")
                f.write("\n")
        
        # Entry points analysis
        f.write("## Entry Points Analysis\n\n")
        f.write(f"Entry points updated to use new CLI: **{'Yes' if entry_points_updated else 'No'}**\n\n")
        f.write("```\n")
        f.write(entry_points_text)
        f.write("\n```\n\n")
        
        # Command comparison
        f.write("## Command Comparison\n\n")
        f.write("### Old Commands\n\n")
        for cmd in command_comparison['old_commands']:
            f.write(f"- {cmd}\n")
        
        f.write("\n### New Commands\n\n")
        for cmd in command_comparison['new_commands']:
            f.write(f"- {cmd}\n")
        
        f.write("\n### Missing Commands\n\n")
        if not command_comparison['missing']:
            f.write("All commands have been migrated.\n")
        else:
            for cmd in command_comparison['missing']:
                f.write(f"- {cmd}\n")
        
        f.write("\n### Successfully Migrated Commands\n\n")
        for cmd in command_comparison['migrated']:
            f.write(f"- {cmd}\n")
        
        # Summary
        f.write("\n## Summary\n\n")
        f.write(f"- Files with references to legacy CLI: {len(references)}\n")
        f.write(f"- Entry points updated: {'Yes' if entry_points_updated else 'No'}\n")
        f.write(f"- Commands migrated: {len(command_comparison['migrated'])}/{len(command_comparison['old_commands'])}\n")
        f.write(f"- Missing commands: {len(command_comparison['missing'])}\n\n")
        
        if len(references) == 0 and entry_points_updated and len(command_comparison['missing']) == 0:
            f.write("✅ **Safe to proceed with removal**\n")
        else:
            f.write("⚠️ **Review required before removal**\n")
    
    print(f"Report generated: {report_file}")
    return report_file

def main():
    parser = argparse.ArgumentParser(description="Analyze legacy CLI dependencies")
    parser.add_argument('--output-dir', default='./', help='Output directory for the report')
    args = parser.parse_args()
    
    analyzer = LegacyCLIAnalyzer()
    report_file = generate_report(analyzer, args.output_dir)
    
    print(f"Verification complete. Report saved to {report_file}")
    
if __name__ == "__main__":
    main()
