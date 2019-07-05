import setuptools

with open("requirements.txt") as f:
    required = f.read().splitlines()

setuptools.setup(
    name="semmatch",
    version="0.0.4",
    author="Albert Xu",
    author_email="albert.t.xu@gmail.com",
    description="template matching tool for SerialEM",
    packages=setuptools.find_packages(),
    install_requires=required,
    entry_points={"console_scripts": ["semmatch = semmatch.__main__:main"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
