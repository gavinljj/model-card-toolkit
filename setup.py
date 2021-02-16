# Copyright 2021 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Setup to install the Model Card Toolkit.

Run with `python3 setup.py sdist bdist_wheel`.
"""

from distutils import spawn
from distutils.command import build

import os
import platform
import subprocess

from setuptools import Command
from setuptools import find_packages
from setuptools import setup

REQUIRED_PACKAGES = [
    'absl-py>=0.9,<0.11',
    'semantic-version>=2.8.0,<3',
    'jinja2>=2.10,<3',
    'matplotlib>=3.2.0,<4',
    'jsonschema>=3.2.0,<4',
    'tensorflow-data-validation>=0.26.0,<0.27.0',
    'tensorflow-model-analysis>=0.26.0,<0.27.0',
    'tensorflow-metadata>=0.26.0,<0.27.0',
    'ml-metadata>=0.26.0,<0.27.0',
    'dataclasses;python_version<"3.7"',
]

# Get version from version module.
with open('model_card_toolkit/version.py') as fp:
  globals_dict = {}
  exec(fp.read(), globals_dict)  # pylint: disable=exec-used
__version__ = globals_dict['__version__']

with open('README.md', 'r', encoding='utf-8') as fh:
  _LONG_DESCRIPTION = fh.read()


class _BuildCommand(build.build):
  """Build everything that is needed to install.

  This overrides the original distutils "build" command to to run bazel_build
  command before any sub_commands.

  build command is also invoked from bdist_wheel and install command, therefore
  this implementation covers the following commands:
    - pip install . (which invokes bdist_wheel)
    - python setup.py install (which invokes install command)
    - python setup.py bdist_wheel (which invokes bdist_wheel command)
  """

  def _build_cc_extensions(self):
    return True

  # Add "bazel_build" command as the first sub_command of "build". Each
  # sub_command of "build" (e.g. "build_py", "build_ext", etc.) is executed
  # sequentially when running a "build" command, if the second item in the tuple
  # (predicate method) is evaluated to true.
  sub_commands = [
      ('bazel_build', _build_cc_extensions),
  ] + build.build.sub_commands


class _BazelBuildCommand(Command):
  """Build Bazel artifacts and move generated files."""

  def initialize_options(self):
    pass

  def finalize_options(self):
    self._bazel_cmd = spawn.find_executable('bazel')
    if not self._bazel_cmd:
      self._bazel_cmd = spawn.find_executable('bazelisk')
    if not self._bazel_cmd:
      raise RuntimeError(
          'Could not find "bazel" or "bazelisk" binary. Please visit '
          'https://docs.bazel.build/versions/master/install.html for '
          'installation instruction.')
    self._additional_build_options = []
    if platform.system() == 'Darwin':  # see b/175182911 for context
      self._additional_build_options = ['--macos_minimum_os=10.9']

  def run(self):
    # Bazel should be invoked in the directory containing the WORKSPACE file.
    mct_dir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), 'model_card_toolkit')
    proto_dir = os.path.join(mct_dir, 'proto')
    subprocess.check_call(
        [
            self._bazel_cmd, 'build', '--verbose_failures',
            *self._additional_build_options, ':model_card_py_pb2'
        ],
        cwd=proto_dir,
    )
    subprocess.check_call(
        [
            self._bazel_cmd, 'run', *self._additional_build_options,
            ':move_generated_files'
        ],
        cwd=mct_dir,
    )


setup(
    name='model-card-toolkit',
    version=__version__,
    description='Model Card Toolkit',
    long_description=_LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='https://github.com/tensorflow/model-card-toolkit',
    author='Google LLC',
    author_email='tensorflow-extended-dev@googlegroups.com',
    packages=find_packages(exclude=('bazel-model_card_toolkit*',)),
    package_data={
        'model_card_toolkit': ['schema/**/*.json', 'template/**/*.jinja']
    },
    python_requires='>=3.6,<4',
    install_requires=REQUIRED_PACKAGES,
    tests_require=REQUIRED_PACKAGES,
    # PyPI package information.
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    license='Apache 2.0',
    keywords='model card toolkit ml metadata machine learning',
    cmdclass={
        'build': _BuildCommand,
        'bazel_build': _BazelBuildCommand,
    })
