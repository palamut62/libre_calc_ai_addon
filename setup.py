"""LibreCalc AI Asistanı kurulum scripti."""

from setuptools import setup, find_packages
from pathlib import Path

# README dosyasını oku
readme_path = Path(__file__).parent / "LibreCalc_AI_Assistant_PRD.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="libre-calc-ai-addon",
    version="1.0.0",
    description="LibreOffice Calc için AI destekli asistan",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="LibreCalc AI Team",
    python_requires=">=3.10",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "PyQt5>=5.15.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "httpx>=0.27.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-mock>=3.0",
        ],
        "speech": [
            "SpeechRecognition>=3.10",
            "vosk>=0.3.45",
        ],
    },
    entry_points={
        "console_scripts": [
            "libre-calc-ai=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business :: Financial :: Spreadsheet",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
)
