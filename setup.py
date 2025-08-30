"""
Flask端口复用扩展安装脚本
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="flask-port-extension",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Flask端口复用扩展 - 让多个Flask应用共享同一个端口",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/flask-port-extension",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Flask",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "optimization": [
            "flask-compress>=1.0.0",
            "flask-caching>=1.10.0",
        ],
        "testing": [
            "pytest>=6.0.0",
            "pytest-cov>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "flask-port-extension=pytools.flask_port_extension.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt"],
    },
)