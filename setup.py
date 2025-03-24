from setuptools import setup, find_packages

setup(
    name="biochat",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "aiohttp",
        "openai",
        "pydantic",
        "tenacity",
        "requests",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="BioChat API for interacting with biological databases through natural language",
    keywords="biology, api, chat, bioinformatics",
    python_requires=">=3.8",
)