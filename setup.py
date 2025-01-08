from setuptools import setup, find_packages

setup(
    name="biochat",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "openai",
        "python-dotenv",
        "requests",
        "pydantic",
    ],
)