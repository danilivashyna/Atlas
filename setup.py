from setuptools import setup, find_packages

setup(
    name="atlas-semantic-space",
    version="0.1.0",
    description="Atlas - Semantic Space Control Panel: A 5D interface between abstract meaning and concrete form",
    author="danilivashyna",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "torch>=1.9.0",
        "transformers>=4.20.0",
        "matplotlib>=3.4.0",
        "plotly>=5.0.0",
        "scikit-learn>=0.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.12",
        ]
    },
    entry_points={
        "console_scripts": [
            "atlas=atlas.cli:main",
        ],
    },
)
