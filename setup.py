from distutils.core import setup
import setup_translate


setup(name='enigma2-plugin-systemplugins-extrafancontrol',
		version='2.4',
		author='Dimitrij openPLi',
		author_email='dima-73@inbox.lv',
		package_dir={'SystemPlugins.ExtraFanControl': 'src'},
		packages=['SystemPlugins.ExtraFanControl'],
		package_data={'SystemPlugins.ExtraFanControl': ['hddtemp.db']},
		description='Extra Fan Control - using CPU/HDD/SSD temp',
		cmdclass=setup_translate.cmdclass,
	)
