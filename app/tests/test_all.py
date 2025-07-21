#!/usr/bin/env python3
"""
Final comprehensive test of all bug fixes.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
sys.path.insert(0, project_root)

import subprocess

def run_test(test_name, test_file):
    """Run a test and return True if it passes."""
    try:
        # Since all test files are now in the same directory, use the current directory
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        result = subprocess.run([sys.executable, test_path], 
                              capture_output=True, text=True, cwd=project_root, 
                              check=False, encoding='utf-8', errors='replace')
        
        # Check if the test passed by looking for "PASSED" in the output
        passed = "PASSED" in result.stdout
        
        print(f"{test_name}: {'✅ PASSED' if passed else '❌ FAILED'}")
        
        if not passed:
            # Show only the last few lines of output for readability
            stdout_lines = result.stdout.split('\n') if result.stdout else []
            stderr_lines = result.stderr.split('\n') if result.stderr else []
            
            if stdout_lines:
                print(f"  last stdout lines: {stdout_lines[-3:]}")
            if stderr_lines:
                print(f"  stderr: {stderr_lines[-1]}")
        
        return passed
    
    except (subprocess.SubprocessError, OSError) as e:
        print(f"{test_name}: ❌ ERROR - {e}")
        return False

def main():
    print("=== Running All Tournament Tests ===\n")
    
    tests = [
        ("Two Player Double Elimination", "test_two_player.py"),
        ("Six Player Tournament", "test_six_player.py"),
        ("XBisch Bug Fix", "test_xbisch_bug.py"),
        ("Complete Tournament", "test_complete_tournament.py"),
        ("Upper Bracket First", "test_upper_first.py"),
        ("Missing Players Check", "test_missing_players.py"),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_file in tests:
        if run_test(test_name, test_file):
            passed_tests += 1
    
    print("\n=== Test Results ===")
    print(f"Passed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The tournament bracket system is working correctly.")
        print("\nKey fixes implemented:")
        print("✅ Fixed players disappearing when upper bracket played first")
        print("✅ Fixed duplicate players in pending queue")
        print("✅ Fixed elimination tracking for all bracket progressions")
        print("✅ Fixed lower bracket winner collection from all completed rounds")
        print("✅ Support for both round-by-round and bracket-by-bracket play")
        return True
    else:
        print(f"❌ {total_tests - passed_tests} tests failed. System needs more work.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
