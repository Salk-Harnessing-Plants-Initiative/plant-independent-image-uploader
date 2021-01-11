import setuptools
import json

def locked_requirements(section):
    """Look through the 'Pipfile.lock' to fetch requirements by section.
    https://stackoverflow.com/a/50957425/14775744"""
    with open('Pipfile.lock') as pip_file:
        pipfile_json = json.load(pip_file)

    if section not in pipfile_json:
        print("{0} section missing from Pipfile.lock".format(section))
        return []

    return [package + detail.get('version', "")
            for package, detail in pipfile_json[section].items()]

setuptools.setup(
    name="aws_s3_desktop_uploader",
    version="0.0.1",
    description="A simple Python package",
    url="https://github.com/Salk-Harnessing-Plants-Initiative/aws-s3-desktop-uploader",
    author="Salk HPI",
    license="MIT",
    packages=setuptools.find_packages(),
    python_requires=">=3",
    install_requires=locked_requirements('default')
)