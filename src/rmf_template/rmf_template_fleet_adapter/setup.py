from setuptools import setup
import os
from glob import glob

package_name = 'rmf_template_fleet_adapter'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='Fleet adapter template for my robot fleet',
    license='Apache 2.0',
    entry_points={
        'console_scripts': [
            'fleet_adapter = rmf_template_fleet_adapter.fleet_adapter:main',
        ],
    },
)
