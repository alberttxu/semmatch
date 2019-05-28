import setuptools

with open('requirements.txt') as f:
    required = f.read().splitlines()

setuptools.setup(
    name="semmatch",
    version="0.1",
    author="Albert Xu",
    author_email="albert.t.xu@gmail.com",
    description="template matching tool for SerialEM",
    packages=setuptools.find_packages(),
    install_requires=required,
    #install_requires=["opencv-python", "PyQt5", "PyQt5-sip", "scipy"],
    scripts=["bin/semmatch"]
)
