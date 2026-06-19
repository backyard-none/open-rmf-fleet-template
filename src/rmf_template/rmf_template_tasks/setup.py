from setuptools import setup

setup(
    name='rmf_template_tasks',
    version='0.1.0',
    packages=['rmf_template_tasks'],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/rmf_template_tasks']),
        ('share/rmf_template_tasks', ['package.xml']),
    ],
    install_requires=['setuptools'],
    entry_points={
        'console_scripts': [
            'dispatch_patrol   = rmf_template_tasks.dispatch_patrol:main',
            'dispatch_delivery = rmf_template_tasks.dispatch_delivery:main',
        ],
    },
)
