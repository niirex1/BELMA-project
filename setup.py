from setuptools import setup, find_packages
from pathlib import Path

readme = Path(__file__).parent / "README.md"
long_description = readme.read_text(encoding="utf-8") if readme.exists() else ""

setup(
    name="belma",
    version="1.1.0",   # 1.1.0 reflects the revision-round changes
    description="BELMA: dual-layer formal verification + LLM-based smart contract repair",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sosu et al.",
    license="Apache-2.0",
    python_requires=">=3.9",
    packages=find_packages(exclude=("tests", "experiments", "docs")),
    include_package_data=True,
    package_data={"belma": ["../configs/*.yaml"]},
    install_requires=[
        "numpy>=1.24", "scipy>=1.10", "pyyaml>=6.0", "networkx>=3.0",
        "scikit-learn>=1.3", "torch>=2.0", "transformers>=4.30",
        "matplotlib>=3.7", "pandas>=2.0", "tqdm>=4.65",
    ],
    entry_points={
        "console_scripts": [
            "belma = belma.pipeline:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
    ],
)
