from setuptools import setup, find_packages

setup(
    name="dbp-cli",
    version="0.1.0",
    description="Documentation-Based Programming CLI Tool",
    author="Documentation-Based Programming Team",
    author_email="info@example.com",
    url="https://github.com/example/dbp-cli",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Documentation",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "colorama>=0.4.4",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.12.0",
            "black>=21.5b2",
            "isort>=5.9.1",
            "mypy>=0.812",
            "flake8>=3.9.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "dbp=dbp_cli.cli:main",
        ],
    },
)
