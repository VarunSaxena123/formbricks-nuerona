from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="formbricks-challenge-cli",
    version="1.0.0",
    author="Formbricks Challenge",
    description="A CLI tool for the Formbricks Challenge",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/formbricks-challenge",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "formbricks-cli=main:app",
        ],
    },
    include_package_data=True,
    package_data={
        "formbricks_cli": ["*.yml", "*.yaml"],
    },
)