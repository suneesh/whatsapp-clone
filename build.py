#!/usr/bin/env python
"""
Build and package the WhatsApp Clone Python Client.

This script:
1. Validates the package structure
2. Builds wheel and source distributions
3. Checks the build artifacts
4. Displays distribution info

Usage:
    python build.py
    python build.py --upload  # Upload to TestPyPI (requires token)
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"Error: Command failed with return code {result.returncode}")
        sys.exit(1)
    return result


def validate_package(client_dir):
    """Validate package structure and metadata."""
    print("\n=== Validating Package ===")
    
    # Check required files
    required_files = [
        "README.md",
        "LICENSE",
        "pyproject.toml",
        "CHANGELOG.md",
        "INSTALLATION.md",
        "MANIFEST.in",
    ]
    
    for file in required_files:
        path = client_dir / file
        if not path.exists():
            print(f"Warning: {file} not found")
        else:
            print(f"✓ {file}")
    
    # Check source code
    src_dir = client_dir / "src" / "whatsapp_client"
    if not src_dir.exists():
        print("Error: src/whatsapp_client not found")
        return False
    
    print(f"✓ Source code found: {src_dir}")
    
    # Check pyproject.toml
    pyproject = client_dir / "pyproject.toml"
    print(f"✓ Build config: {pyproject}")
    
    return True


def build_package(client_dir):
    """Build wheel and source distributions."""
    print("\n=== Building Package ===")
    
    # Install/upgrade build tools
    print("Installing build tools...")
    run_command([
        sys.executable, "-m", "pip", "install",
        "--upgrade", "pip", "setuptools", "wheel", "build"
    ])
    
    # Build distribution
    print("Building distributions...")
    run_command([
        sys.executable, "-m", "build"
    ], cwd=str(client_dir))
    
    return True


def check_artifacts(client_dir):
    """Check and display build artifacts."""
    print("\n=== Build Artifacts ===")
    
    dist_dir = client_dir / "dist"
    if not dist_dir.exists():
        print("Error: dist directory not found")
        return False
    
    artifacts = list(dist_dir.glob("*"))
    if not artifacts:
        print("Error: No build artifacts found")
        return False
    
    print(f"Found {len(artifacts)} artifacts:")
    total_size = 0
    
    for artifact in artifacts:
        size_kb = artifact.stat().st_size / 1024
        total_size += size_kb
        print(f"  • {artifact.name:50} ({size_kb:10.2f} KB)")
    
    print(f"\nTotal size: {total_size / 1024:.2f} MB")
    
    # Check wheel metadata
    wheels = list(dist_dir.glob("*.whl"))
    if wheels:
        print(f"\n{len(wheels)} wheel(s) built:")
        for wheel in wheels:
            print(f"  • {wheel.name}")
    
    # Check source distribution
    sdists = list(dist_dir.glob("*.tar.gz"))
    if sdists:
        print(f"\n{len(sdists)} source distribution(s) built:")
        for sdist in sdists:
            print(f"  • {sdist.name}")
    
    return True


def validate_package_integrity(client_dir):
    """Validate package contents."""
    print("\n=== Validating Package Integrity ===")
    
    dist_dir = client_dir / "dist"
    
    # Check wheel contents
    wheels = list(dist_dir.glob("*.whl"))
    for wheel in wheels:
        print(f"Checking {wheel.name}...")
        result = subprocess.run(
            [sys.executable, "-m", "zipfile", "-l", str(wheel)],
            capture_output=True,
            text=True,
        )
        
        lines = result.stdout.split('\n')
        print(f"  Contains {len([l for l in lines if l.strip()])} entries")
        
        # Check for critical files
        if "whatsapp_client/__init__.py" in result.stdout:
            print("  ✓ Contains __init__.py")
        else:
            print("  ✗ Missing __init__.py")
    
    # Check source distribution
    sdists = list(dist_dir.glob("*.tar.gz"))
    for sdist in sdists:
        print(f"Checking {sdist.name}...")
        result = subprocess.run(
            [sys.executable, "-m", "tarfile", "-l", str(sdist)],
            capture_output=True,
            text=True,
        )
        
        lines = result.stdout.split('\n')
        print(f"  Contains {len([l for l in lines if l.strip()])} entries")


def test_installation(client_dir):
    """Test installing the package."""
    print("\n=== Testing Installation ===")
    
    wheels = list((client_dir / "dist").glob("*.whl"))
    if not wheels:
        print("No wheels found to test")
        return False
    
    wheel = wheels[0]
    print(f"Testing installation of {wheel.name}...")
    
    # Create test environment
    test_venv = client_dir / "test_venv"
    if test_venv.exists():
        import shutil
        shutil.rmtree(test_venv)
    
    # Create virtual environment
    subprocess.run([sys.executable, "-m", "venv", str(test_venv)])
    
    # Get pip path for venv
    if sys.platform == "win32":
        pip_path = test_venv / "Scripts" / "pip"
    else:
        pip_path = test_venv / "bin" / "pip"
    
    # Install wheel
    print(f"Installing {wheel.name}...")
    subprocess.run([str(pip_path), "install", str(wheel)])
    
    # Test import
    if sys.platform == "win32":
        python_path = test_venv / "Scripts" / "python"
    else:
        python_path = test_venv / "bin" / "python"
    
    result = subprocess.run(
        [str(python_path), "-c", "from whatsapp_client import AsyncClient; print('Success!')"],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        print(f"✓ {result.stdout.strip()}")
        return True
    else:
        print(f"✗ Import failed: {result.stderr}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build WhatsApp Clone Python Client"
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload to TestPyPI",
    )
    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="Skip installation test",
    )
    
    args = parser.parse_args()
    
    # Get client directory
    script_dir = Path(__file__).parent
    client_dir = script_dir / "python-client"
    
    if not client_dir.exists():
        print(f"Error: {client_dir} not found")
        sys.exit(1)
    
    print(f"Building package in: {client_dir}")
    
    # Validate
    if not validate_package(client_dir):
        sys.exit(1)
    
    # Build
    if not build_package(client_dir):
        sys.exit(1)
    
    # Check artifacts
    if not check_artifacts(client_dir):
        sys.exit(1)
    
    # Validate integrity
    validate_package_integrity(client_dir)
    
    # Test installation
    if not args.skip_test:
        test_installation(client_dir)
    
    print("\n✓ Package build completed successfully!")
    print(f"Artifacts in: {client_dir / 'dist'}")


if __name__ == "__main__":
    main()
