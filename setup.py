from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="c_code_analyzer",
    version="0.1.0",
    author="Author",
    author_email="author@example.com",
    description="A tool for analyzing business logic in C code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/username/c_code_analyzer",
    packages=find_packages(where="src"),
    package_dir={"":"src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyclang>=0.2.1",
        "networkx>=3.1",
        "matplotlib>=3.7.1",
        "pydot>=1.4.2",
        "graphviz>=0.20.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "isort>=5.0",
            "flake8>=4.0",
            "sphinx>=4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "analyze-c-code=c_code_analyzer.cli.commands:main",
        ],
    },
)