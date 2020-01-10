import setuptools

setuptools.setup(
    name="semmatch",
    version="0.0.15",
    author="Albert Xu",
    author_email="albert.t.xu@gmail.com",
    description="template matching tool for SerialEM",
    packages=setuptools.find_packages(),
    install_requires=[
        "imageio",
        "numpy",
        "opencv-python",
        "PyQt5",
        "Pillow",
        "scikit-image",
        "scikit-learn",
        "scipy",
    ],
    entry_points={"console_scripts": ["semmatch = semmatch.__main__:main"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
