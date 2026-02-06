from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="ADB-Manager",
    version="0.1.0",
    author="Galkurta",
    description="A modern GUI wrapper for Android Debug Bridge",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Galkurta/ADB-Manager",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=[
        "PySide6>=6.6.0",
        "PySide6-Addons>=6.6.0",
        "qasync>=0.24.0",
        "aiofiles>=23.2.1",
        "opencv-python>=4.8.0",
        "av>=11.0.0",
        "numpy>=1.24.0",
        "psutil>=5.9.0",
        "watchdog>=3.0.0",
        "cryptography>=41.0.0",
        "Pillow>=10.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-qt>=4.2.0",
            "black>=23.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ADB-Manager=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["resources/**/*", "binaries/**/*"],
    },
)
