# -*- coding: utf-8 -*-
"""
Windows Encoding Auto-Fix Script
=================================

This script automatically adds Windows encoding fixes to all paper trading files.
Run this once to fix all Unicode/charmap errors.
"""

import os
import sys

# Encoding fix code to add at the top of files
ENCODING_FIX = '''# -*- coding: utf-8 -*-
import sys
import io

# ============================
# FIX WINDOWS CONSOLE ENCODING
# ============================
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

'''

def has_encoding_fix(content):
    """Check if file already has encoding fix"""
    return 'FIX WINDOWS CONSOLE ENCODING' in content or 'sys.stdout.reconfigure' in content


def add_encoding_fix(filepath):
    """Add encoding fix to a Python file"""
    try:
        # Read the file
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception as e:
            print(f"[X] Error reading {filepath}: {e}")
            return False
    except Exception as e:
        print(f"[X] Error reading {filepath}: {e}")
        return False
    
    # Check if already has fix
    if has_encoding_fix(content):
        print(f"[SKIP] {filepath} - Already has encoding fix")
        return True
    
    # Find the first import or code line
    lines = content.split('\n')
    insert_position = 0
    
    # Skip shebang and existing encoding declarations
    for i, line in enumerate(lines):
        if line.startswith('#') and (line.startswith('#!') or 'coding' in line.lower()):
            insert_position = i + 1
        elif line.strip() and not line.strip().startswith('#'):
            # First non-comment line found
            break
    
    # Insert encoding fix
    new_lines = lines[:insert_position] + ENCODING_FIX.split('\n') + lines[insert_position:]
    new_content = '\n'.join(new_lines)
    
    # Write back
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[OK] {filepath} - Encoding fix added")
        return True
    except Exception as e:
        print(f"[X] Error writing {filepath}: {e}")
        return False


def main():
    """Main function"""
    print("\n" + "="*80)
    print("WINDOWS ENCODING AUTO-FIX SCRIPT")
    print("="*80)
    print("\nThis script will add Windows encoding fixes to all paper trading files.")
    print("This will fix Unicode/charmap errors when running on Windows.\n")
    
    # Files to fix
    files_to_fix = [
        'verify_setup.py',
        'test_paper_trading.py',
        'paper_trading_simulator.py',
        'paper_trading_wrapper.py',
    ]
    
    print(f"Files to process: {len(files_to_fix)}\n")
    
    fixed_count = 0
    skipped_count = 0
    error_count = 0
    
    for filepath in files_to_fix:
        if not os.path.exists(filepath):
            print(f"[SKIP] {filepath} - File not found")
            skipped_count += 1
            continue
        
        result = add_encoding_fix(filepath)
        if result:
            if has_encoding_fix(open(filepath, 'r', encoding='utf-8').read()):
                fixed_count += 1
        else:
            error_count += 1
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Files processed: {len(files_to_fix)}")
    print(f"Fixed:           {fixed_count}")
    print(f"Skipped:         {skipped_count}")
    print(f"Errors:          {error_count}")
    
    if error_count == 0:
        print("\n[SUCCESS] All files processed successfully!")
        print("\nYou can now run:")
        print("   python verify_setup.py")
        print("   python test_paper_trading.py")
    else:
        print("\n[WARNING] Some files had errors. Check messages above.")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
