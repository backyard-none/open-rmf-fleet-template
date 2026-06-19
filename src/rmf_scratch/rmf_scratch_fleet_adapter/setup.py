from setuptools import setup
import os
from glob import glob

package_name = 'rmf_scratch_fleet_adapter'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
         glob('launch/*.launch.xml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='antigravity',
    maintainer_email='antigravity@gemini.com',
    description='Custom fleet adapter for scratch project',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'fleet_adapter = rmf_scratch_fleet_adapter.fleet_adapter:main',
            'fleet_manager = rmf_scratch_fleet_adapter.fleet_manager:main',
        ],
    },
)
