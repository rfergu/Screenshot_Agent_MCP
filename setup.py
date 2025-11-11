from setuptools import setup, find_packages

setup(
    name="screenshot_organizer",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        # Keep minimal here; use requirements.txt for development
    ],
    entry_points={
        "console_scripts": [
            "screenshot-organizer=src.__main__:main"
        ]
    }
)
