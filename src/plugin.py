from Plugins.Plugin import PluginDescriptor
from Components.Harddisk import harddiskmanager
from Screens.Screen import Screen
from Screens import Standby
from Screens.ChoiceBox import ChoiceBox
from Components.Pixmap import Pixmap
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, getConfigListEntry, ConfigClock, ConfigYesNo, ConfigBoolean, ConfigText, NoSave, ConfigSlider, configfile, ConfigNothing
from time import localtime
from enigma import eTimer, getDesktop
from Screens.MessageBox import MessageBox
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
import os
import gettext
from Components.ActionMap import ActionMap
from Components.Label import Label
from Tools.HardwareInfo import HardwareInfo
try:
	device_name = HardwareInfo().get_device_name()
except:
	device_name = None
from HddTempWatcher import HddTempWatcher

lang = language.getLanguage()
os.environ["LANGUAGE"] = lang[:2]
gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
gettext.textdomain("enigma2")
gettext.bindtextdomain("ExtraFanControl", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "SystemPlugins/ExtraFanControl/locale/"))


def _(txt):
	t = gettext.dgettext("ExtraFanControl", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

# all fan modes:
# 1 - always OFF
# 2 - always ON
# 3 - always AUTO (in wakeup mode - always ON, in standby mode: on idle - OFF, on recording and etc. - ON)
# 4 - on time set (startime:endtime) OFF|ON|AUTO
# 5 - on hdd sleeping set OFF
# 6 - on hdd temperature set ON
# 7 - on system temperature set ON
# 8 - on cpu silicon temperature set ON
# 9 - fan speed if available OFF|ON
# 10 - alternative fan speed if available OFF|ON
# 11 - fan speed in standby if available OFF|ON
#
# configs:
# 1. Fan modes: OFF, ON, AUTO
# 2. Switch OFF mode on time setting: enable|disable
# 2.1. Start time: HH:MM
# 2.1. End time: HH:MM
# 3. Watch on HDD state: None|Sleeping|Temperature
# 3.1. Select internal HDD device: all|+mutable_hdd-device_list
# 3.2. Switch OFF mode on HDD sleep: enable|disable
# or
# 3.2. Switch ON mode on HDD maximum temperature (0 - off): 0-80
# 4. Watch on HDD state(if available): None|System|CPU
# 4.1. Switch ON mode on system maximum temperature (0 - off): 0-80
#or
# 4.1. Switch ON mode on cpu silicon maximum temperature (0 - off): 0-120
# 5. Fan speed if available 0-255 pm
# 5.1. Alternative fan speed if available 0-255 pm
# 5.2. Alternative fan speed  in standby if available 0-255 pm
# 6. Switch fan speed on time setting: yes|no
# 6.1. Start time: HH:MM
# 6.1. End time: HH:MM
# 6.2. Speed if available 0-255 pm


try:
	fd = open('/proc/stb/fp/fan', 'r')
	mode = fd.read().strip()
	fd.close()
	fan_mode = mode
except:
	fan_mode = None

BOX_NAME = "none"
MODEL_NAME = "none"
if os.path.exists("/proc/stb/info/boxtype"):
	BOX_NAME = "all"
	try:
		f = open("/proc/stb/info/boxtype")
		MODEL_NAME = f.read().strip()
		f.close()
	except:
		pass
elif os.path.exists("/proc/stb/info/hwmodel"):
	BOX_NAME = "all"
	try:
		f = open("/proc/stb/info/hwmodel")
		MODEL_NAME = f.read().strip()
		f.close()
	except:
		pass
elif os.path.exists("/proc/stb/info/vumodel"):
	BOX_NAME = "vu"
	try:
		f = open("/proc/stb/info/vumodel")
		MODEL_NAME = f.read().strip()
		f.close()
	except:
		pass
elif device_name and device_name.startswith('dm') and os.path.exists("/proc/stb/info/model"):
	BOX_NAME = "dmm"
	try:
		f = open("/proc/stb/info/model")
		MODEL_NAME = f.read().strip()
		f.close()
	except:
		pass


modelist = [("off", _("Off")), ("on", _("On"))]
if os.path.exists("/proc/stb/fp/fan_choices"):
	try:
		modelist = [x for x in modelist if x[0] in open("/proc/stb/fp/fan_choices", "r").read().strip().split(" ")]
	except:
		pass
modelist += [("auto", _("Auto"))]
modelist += [("standby", _("Fan - off in standby"))]
default_auto = False
if MODEL_NAME == "osmega":
	default_auto = True
timsetlist = modelist[:]
timsetlist += [("none", _("None"))]
hddwatchlist = {"none": _("None"), "sleep": _("HDD/SSD sleeping"), "temp": _("HDD/SSD temperature")}
timsetlist = {"none": _("None"), "off": _("Off"), "on": _("On"), "auto": _("Auto")}
intervallist = [("60", "60"), ("90", "90"), ("120", "120"), ("180", "180")]
standbylist = [("equal", _("Equal")), ("other", _("Other"))]

try:
	fd = open('/proc/stb/fp/fan_pwm', 'r')
	pwm = fd.read().strip()
	fd.close()
	fan_speed = pwm
except:
	fan_speed = None

boardwatchlist = {"none": _("None")}
try:
	system_temp = None
	if os.path.exists('/proc/stb/sensors/temp/value'):
		fd = open('/proc/stb/sensors/temp/value', 'r')
		temp = int(fd.read().strip(), 0)
		fd.close()
	elif os.path.exists('/proc/stb/fp/temp_sensor'):
		fd = open('/proc/stb/fp/temp_sensor', 'r')
		temp = int(fd.read().strip(), 0)
		fd.close()
	if temp == 0:
		system_temp = None
	else:
		system_temp = temp
		boardwatchlist = {"none": _("None"), "system": _("System temperature")}
except:
	system_temp = None

try:
	fd = open('/proc/stb/fp/temp_sensor_avs', 'r')
	temp = int(fd.read().strip(), 0)
	fd.close()
	cpu_temp = temp
	boardwatchlist = {"none": _("None"), "cpu": _("CPU silicon temperature")}
except:
	cpu_temp = None

if cpu_temp is not None and system_temp is not None:
	boardwatchlist = {"none": _("None"), "system": _("System temperature"), "cpu": _("CPU silicon temperature")}

config.plugins.extrafancontrol = ConfigSubsection()
try:
	config.plugins.extrafancontrol.mode = config.usage.fan
	config.plugins.extrafancontrol.mode.setChoices(modelist)
except:
	config.plugins.extrafancontrol.mode = ConfigSelection(choices=modelist, default="on")
config.plugins.extrafancontrol.timeset = ConfigSelection(choices=timsetlist, default="none")
config.plugins.extrafancontrol.timestartoff = ConfigClock(default=((21 * 60 + 30) * 60))
config.plugins.extrafancontrol.timeendoff = ConfigClock(default=((7 * 60 + 0) * 60))
config.plugins.extrafancontrol.usealttime = ConfigYesNo(default=False)
config.plugins.extrafancontrol.alt_timestart = ConfigClock(default=((21 * 60 + 30) * 60))
config.plugins.extrafancontrol.alt_timeend = ConfigClock(default=((7 * 60 + 0) * 60))
config.plugins.extrafancontrol.hddwatch = ConfigSelection(choices=hddwatchlist, default="none")
config.plugins.extrafancontrol.hdddevice = ConfigText(default="all")
config.plugins.extrafancontrol.hddsleep = ConfigYesNo(default=False)
config.plugins.extrafancontrol.hddtemp = ConfigInteger(0, limits=(0, 80))
config.plugins.extrafancontrol.interval = ConfigSelection(choices=intervallist, default="120")
config.plugins.extrafancontrol.interval_tempwatcher = ConfigSelection(choices=[("30", "30"), ("45", "45")] + intervallist, default="60")
config.plugins.extrafancontrol.menuhdd = ConfigYesNo(default=False)
config.plugins.extrafancontrol.alt_auto = ConfigYesNo(default=default_auto)
config.plugins.extrafancontrol.warning = NoSave(ConfigNothing())
try:
	config.plugins.extrafancontrol.fanspeed = config.usage.fanspeed
	isSetPMW = False
except:
	isSetPMW = True
	config.plugins.extrafancontrol.fanspeed = ConfigSlider(default=127, increment=8, limits=(0, 255))
config.plugins.extrafancontrol.altfanspeed = ConfigSlider(default=127, increment=8, limits=(0, 255))
config.plugins.extrafancontrol.standbyfanspeed = ConfigSlider(default=127, increment=8, limits=(0, 255))
config.plugins.extrafancontrol.timeset = ConfigSelection(choices=timsetlist, default="none")
config.plugins.extrafancontrol.usealtfanspeed = ConfigYesNo(default=False)
config.plugins.extrafancontrol.systemtemp = ConfigInteger(0, limits=(0, 80))
config.plugins.extrafancontrol.cputemp = ConfigInteger(0, limits=(0, 120))
config.plugins.extrafancontrol.speedstandby = ConfigSelection(choices=standbylist, default="equal")
config.plugins.extrafancontrol.syswatch = ConfigSelection(choices=boardwatchlist, default="none")

tempwatcher = None
fanmanager = None

plugin_version = "2.6"

FULLHD = False
if getDesktop(0).size().width() >= 1920:
	FULLHD = True


class ExtraFanControlScreen(Screen, ConfigListScreen):
	if FULLHD:
		skin = """
			<screen position="center,center" size="900,740" >
				<widget name="key_red" position="0,0" size="240,60" zPosition="5" transparent="1" halign="center" valign="center" foregroundColor="white" font="Regular;25" shadowColor="background" shadowOffset="-2,-2" />
				<widget name="key_green" position="240,0" size="240,60" zPosition="5" transparent="1" halign="center" valign="center" foregroundColor="white" font="Regular;25" shadowColor="background" shadowOffset="-2,-2" />
				<widget name="key_yellow" position="490,0" size="240,60" zPosition="5" transparent="1" halign="center" valign="center" foregroundColor="white" font="Regular;25" shadowColor="background" shadowOffset="-2,-2" />
				<ePixmap name="red" pixmap="skin_default/buttons/red.png" position="0,0" size="250,60" zPosition="4" transparent="1" alphatest="on" />
				<ePixmap name="green" pixmap="skin_default/buttons/green.png" position="250,0" size="250,60" zPosition="4" transparent="1" alphatest="on" />
				<ePixmap name="yellow" pixmap="skin_default/buttons/yellow.png" position="500,0" size="250,60" zPosition="4" transparent="1" alphatest="on" />
				<widget name="config" position="10,70" size="880,480" itemHeight="35" font="Regular;33" />
				<ePixmap pixmap="skin_default/div-h.png" position="0,560" zPosition="1" size="900,5" />
				<widget name="systemTemp" foregroundColor="#00ffc000" position="10,580" size="700,27" font="Regular;25" zPosition="1" transparent="1" />
				<widget name="cpuTemp" foregroundColor="#00ffc000" position="10,620" size="700,27" font="Regular;25" zPosition="1" transparent="1" />
				<widget name="fanSpeed" foregroundColor="#00ffc000" position="10,660" size="700,27" font="Regular;25" zPosition="1" transparent="1" />
				<ePixmap pixmap="skin_default/div-h.png" position="0,680" zPosition="1" size="900,5" />
				<widget name="powerstatus" position="10,700" size="300,35" font="Regular;32" zPosition="1" transparent="1" />
				<widget name="daemon0" alphatest="on" pixmap="skin_default/buttons/button_green_off.png" position="320,710" size="80,80" zPosition="10" transparent="1"/>
				<widget name="daemon1" alphatest="on" pixmap="skin_default/buttons/button_green.png" position="320,710" size="80,80" zPosition="10" transparent="1"/>
			</screen>
		"""
	else:
		skin = """
			<screen position="center,center" size="565,490" >
				<ePixmap name="red" position="0,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
				<ePixmap name="green" position="140,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
				<ePixmap name="yellow" position="280,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
				<widget name="key_red" position="0,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;17" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
				<widget name="key_green" position="140,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;17" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
				<widget name="key_yellow" position="280,0" size="138,38" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;17" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
				<widget name="config" position="0,45" size="565,328" />
				<ePixmap pixmap="skin_default/div-h.png" position="0,375" zPosition="1" size="565,2" />
				<widget name="systemTemp" foregroundColor="#00ffc000" position="10,380" size="300,21" font="Regular;19" zPosition="1" transparent="1" />
				<widget name="cpuTemp" foregroundColor="#00ffc000" position="10,405" size="300,21" font="Regular;19" zPosition="1" transparent="1" />
				<widget name="fanSpeed" foregroundColor="#00ffc000" position="10,430" size="300,21" font="Regular;19" zPosition="1" transparent="1" />
				<ePixmap pixmap="skin_default/div-h.png" position="0,458" zPosition="1" size="565,2" />
				<widget name="powerstatus" position="10,465" size="180,21" font="Regular;19" zPosition="1" transparent="1" />
				<widget name="daemon0" alphatest="on" pixmap="skin_default/buttons/button_green_off.png" position="200,468" size="15,16" zPosition="10" transparent="1"/>
				<widget name="daemon1" alphatest="on" pixmap="skin_default/buttons/button_green.png" position="200,468" size="15,16" zPosition="10" transparent="1"/>
				<ePixmap alphatest="on" pixmap="skin_default/icons/clock.png" position="462,465" size="14,14" zPosition="1" />
				<widget  source="global.CurrentTime" font="Regular;18" halign="left" position="482,465" render="Label" size="55,21" transparent="1" valign="center" zPosition="1">
					<convert type="ClockToText">Default</convert>
				</widget>
				<widget source="global.CurrentTime" font="Regular;15" halign="left" position="532,461" render="Label" size="27,17" transparent="1" valign="center" zPosition="1">
					<convert type="ClockToText">Format::%S</convert>
				</widget>
			</screen>
		"""

	def __init__(self, session, args=None):
		self.skin = ExtraFanControlScreen.skin
		self.setup_title = _("Extra fan control") + _(" - version: ") + plugin_version
		self.powerTimer = eTimer()
		self.tempTimer = eTimer()
		self.internal_hdd = False
		self.fanspeedcontrol = fan_speed
		self.systemtempsensor = system_temp
		self.cputempsensor = cpu_temp
		self.isTBoardtemp = self.systemtempsensor is not None or self.cputempsensor is not None
		self.curmode = None
		self.powerTimer.callback.append(self.getCurrentMode)
		self.tempTimer.callback.append(self.updateTemps)
		Screen.__init__(self, session)
		self["powerstatus"] = Label(_("Power status"))
		self["key_green"] = Label(_("Save/OK"))
		self["key_red"] = Label(_("Cancel"))
		self["key_yellow"] = Label()
		self["systemTemp"] = Label()
		self["cpuTemp"] = Label()
		self["fanSpeed"] = Label()
		self["daemon0"] = Pixmap()
		self["daemon0"].hide()
		self["daemon1"] = Pixmap()
		self["daemon1"].hide()
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.keyOk,
			"cancel": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
		}, -2)
		ConfigListScreen.__init__(self, [], on_change=self.changedEntry)
		self.prev_menuhdd = config.plugins.extrafancontrol.menuhdd.value
		self.prev_interval_tempwatcher = config.plugins.extrafancontrol.interval_tempwatcher.value
		self.initConfig()
		self.createSetup()
		self.onClose.append(self.__closed)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __closed(self):
		self.powerTimer.stop()
		self.tempTimer.stop()

	def __layoutFinished(self):
		self.setTitle(self.setup_title)
		self.tempTimer.start(100, True)
		self.powerTimer.start(100, True)

	def getCurrentMode(self):
		power = None
		try:
			fd = open('/proc/stb/fp/fan', 'r')
			power = fd.read().strip()
			fd.close()
		except:
			pass
		self.curmode = power
		if self.curmode:
			if self.curmode == "off":
				self["daemon1"].hide()
				self["daemon0"].show()
			else:
				self["daemon0"].hide()
				self["daemon1"].show()
		else:
			self["powerstatus"].setText(_("Power status") + ' n/a')
		self.powerTimer.start(2500, True)

	def updateTemps(self):
		if self.isTBoardtemp:
			if self.systemtempsensor:
				temp = getSystemTemp()
				if temp is not None:
					self["systemTemp"].setText(_("System temperature: ") + str(temp) + str('\xc2\xb0') + ' C')
			if self.cputempsensor:
				cputemp = getCPUtemp()
				if cputemp is not None:
					self["cpuTemp"].setText(_("CPU temperature: ") + str(cputemp) + str('\xc2\xb0') + ' C')
		if self.fanspeedcontrol is not None:
			speed = getPWM()
			if speed is not None:
				self["fanSpeed"].setText(_("Current speed: ") + str(speed) + ' pwm')
		self.tempTimer.start(10000, True)

	def getHddList(self):
		hddlist = {}
		self.internal_hdd = False
		for hdd in harddiskmanager.HDDList():
			if "pci" in hdd[1].phys_path or "ahci" in hdd[1].phys_path or "sata" in hdd[1].phys_path:
				devdir = hdd[1].getDeviceDir()
				name = hdd[1].model()
				if name in ("", "-?-"):
					name = devdir
				hddlist[devdir] = name
				self.internal_hdd = True
		return hddlist

	def initConfig(self):
		def getPrevValues(section):
			res = {}
			for (key, val) in section.content.items.items():
				if isinstance(val, ConfigSubsection):
					res[key] = getPrevValues(val)
				else:
					res[key] = val.value
			return res
		self.FAN = config.plugins.extrafancontrol
		self.prev_values = getPrevValues(self.FAN)
		self.cfg_mode = getConfigListEntry(_("Fan mode"), self.FAN.mode)
		self.cfg_alt_auto = getConfigListEntry(_("Use mode 'Auto' from image"), self.FAN.alt_auto)
		self.cfg_timeset = getConfigListEntry(_("Alternative mode for period time"), self.FAN.timeset)
		self.cfg_hddwatch = getConfigListEntry(_("Watch HDD/SSD state"), self.FAN.hddwatch)
		self.cfg_interval = getConfigListEntry(_("Checking interval mode in seconds"), self.FAN.interval)
		self.cfg_interval_tempwatcher = getConfigListEntry(_("Checking interval 'HddTempWatcher' in seconds"), self.FAN.interval_tempwatcher)
		hddlist = self.getHddList()
		if not self.internal_hdd:
			self.FAN.hdddevice.value = "all"
			self.FAN.hddwatch.value = "none"
		else:
			self["key_yellow"].setText(_("HDD/SSD temperature"))
		hddlist["all"] = _("All")
		default = self.FAN.hdddevice.value not in hddlist and "all" or self.FAN.hdddevice.value
		self.hddlistsel = NoSave(ConfigSelection(choices=hddlist, default=default))
		self.cfg_hdddevice = getConfigListEntry(_("Select internal HDD/SSD device"), self.hddlistsel)
		self.cfg_syswatch = getConfigListEntry(_("Watch board temp"), self.FAN.syswatch)
		self.cfg_fanspeed = getConfigListEntry(_("Fan speed"), self.FAN.fanspeed)
		self.cfg_usealtfanspeed = getConfigListEntry(_("Use alternative fan speed"), self.FAN.usealtfanspeed)
		self.cfg_usealttime = getConfigListEntry(_("Period time for alternative speed"), self.FAN.usealttime)
		self.cfg_altfanspeed = getConfigListEntry(_("Speed"), self.FAN.altfanspeed)
		self.cfg_speedstandby = getConfigListEntry(_("Speed in standby"), self.FAN.speedstandby)
		self.cfg_standbyfanspeed = getConfigListEntry(_("Speed"), self.FAN.standbyfanspeed)
		self.cfg_menuhdd = getConfigListEntry(_("Show HDD/SSD temp in extensions menu"), self.FAN.menuhdd)
		self.prev_hdddevice = self.FAN.hdddevice.value

	def createSetup(self):
		list = [self.cfg_mode]
		if not MODEL_NAME.startswith("et"):
			list.append(self.cfg_alt_auto)
			list.append(getConfigListEntry(_("'Auto' mode - off in standby (exception recording)"), self.FAN.warning))
		if self.fanspeedcontrol is not None:
			list.append(self.cfg_fanspeed)
			if self.FAN.mode.value != "standby":
				list.append(self.cfg_speedstandby)
				if self.FAN.speedstandby.value == "other":
					list.append(self.cfg_standbyfanspeed)
		if self.FAN.mode.value != "off" and self.FAN.mode.value != "standby":
			list.append(self.cfg_timeset)
			if self.FAN.timeset.value != "none":
				list.append(getConfigListEntry(_("Start time"), self.FAN.timestartoff))
				list.append(getConfigListEntry(_("End time"), self.FAN.timeendoff))
				if self.fanspeedcontrol is not None and self.FAN.timeset.value != "off":
					list.append(self.cfg_usealtfanspeed)
					if self.FAN.usealtfanspeed.value:
						list.append(self.cfg_altfanspeed)
		elif self.FAN.mode.value == "off":
			if self.internal_hdd:
				list.append(self.cfg_hddwatch)
				if self.FAN.hddwatch.value != "none":
					list.append(self.cfg_hdddevice)
					if self.FAN.hddwatch.value == "temp":
						list.append(getConfigListEntry(_("'On' mode when HDD/SSD max temp (0-disabled)"), self.FAN.hddtemp))
					elif self.FAN.hddwatch.value == "sleep":
						list.append(getConfigListEntry(_("'Off' mode when HDD/SSD sleep"), self.FAN.hddsleep))
			if self.isTBoardtemp:
				list.append(self.cfg_syswatch)
				if self.FAN.syswatch.value != "none":
					if self.FAN.syswatch.value == "system":
						list.append(getConfigListEntry(_("'On' mode when system max temp (0-disabled)"), self.FAN.systemtemp))
					elif self.FAN.syswatch.value == "cpu":
						list.append(getConfigListEntry(_("'On' mode when BCM silicon max temp (0-disabled)"), self.FAN.cputemp))
			if self.isTBoardtemp or self.internal_hdd:
				if self.fanspeedcontrol is not None and self.FAN.syswatch.value != "none" or self.FAN.hddwatch.value != "none":
					list.append(self.cfg_usealttime)
					if self.FAN.usealttime.value:
						list.append(getConfigListEntry(_("Start time"), self.FAN.alt_timestart))
						list.append(getConfigListEntry(_("End time"), self.FAN.alt_timeend))
						list.append(self.cfg_altfanspeed)
		list.append(self.cfg_interval)
		if self.internal_hdd and self.FAN.menuhdd.value:
			list.append(self.cfg_interval_tempwatcher)
		if not os.path.exists("/usr/sbin/hddtemp"):
			list.append(getConfigListEntry(_("HDDtemp not installed!"), self.FAN.warning))
			self.FAN.menuhdd.value = False
		else:
			list.append(self.cfg_menuhdd)
		self["config"].list = list
		self["config"].l.setList(list)

	def newConfig(self):
		cur = self["config"].getCurrent()
		if cur is None:
			return
		if cur in (self.cfg_mode, self.cfg_timeset, self.cfg_hddwatch, self.cfg_syswatch, self.cfg_usealtfanspeed, self.cfg_usealttime, self.cfg_speedstandby, self.cfg_menuhdd):
			if cur == self.cfg_syswatch and self.FAN.syswatch.value != "none":
				self.FAN.hddwatch.value = "none"
			elif cur == self.cfg_hddwatch and self.FAN.hddwatch.value != "none":
				self.FAN.syswatch.value = "none"
			self.createSetup()
		elif cur == self.cfg_hdddevice:
			if self.internal_hdd:
				self.FAN.hdddevice.value = self.hddlistsel.value
		elif cur == self.cfg_fanspeed:
			if self.fanspeedcontrol is not None:
				speed = getPWM()
				if speed is not None:
					self["fanSpeed"].setText(_("Current speed: ") + str(speed) + ' pwm')

	def keyOk(self):
		self.keyGreen()

	def keyRed(self):
		def setPrevValues(section, values):
			for (key, val) in section.content.items.items():
				value = values.get(key, None)
				if value is not None:
					if isinstance(val, ConfigSubsection):
						setPrevValues(val, value)
					else:
						val.value = value
		setPrevValues(self.FAN, self.prev_values)
		self.keyGreen()

	def keyGreen(self):
		if MODEL_NAME == "osmega" and not os.path.exists("/etc/rc0.d/K99stop_fan"):
			os.system("echo -e '#!/bin/sh\n\n\necho off > /proc/stb/fp/fan\n\nexit 0' > /etc/rc0.d/K99stop_fan && chmod 755 /etc/r0.d/K99stop_fan")
		timehddsleep = config.usage.hdd_standby.value
		timeset = config.plugins.extrafancontrol.timeset.value
		mode = config.plugins.extrafancontrol.mode.value
		if self.fanspeedcontrol is None:
			self.FAN.usealttime.value = False
		elif self.FAN.speedstandby.value == "equal":
			self.FAN.standbyfanspeed.value = self.FAN.fanspeed.value
		if not self.internal_hdd:
			self.FAN.hdddevice.value = "all"
			self.FAN.hddwatch.value = "none"
			self.FAN.interval_tempwatcher.value = "60"
			self.FAN.hddsleep.value = False
			self.FAN.hddtemp.value = 0
		if not self.isTBoardtemp:
			self.FAN.syswatch.value = "none"
			self.FAN.systemtemp.value = 0
			self.FAN.cputemp.value = 0
			self.FAN.usealttime.value = False
		if mode == timeset:
			if self.fanspeedcontrol is None:
				self.FAN.timeset.value = "none"
				self.FAN.usealtfanspeed.value = False
		if mode == "off" or mode == "standby":
			self.FAN.timeset.value = "none"
			self.FAN.usealtfanspeed.value = False
		if mode != "off":
			self.FAN.hddwatch.value = "none"
			self.FAN.hddsleep.value = False
			self.FAN.hddtemp.value = 0
			self.FAN.syswatch.value = "none"
			self.FAN.systemtemp.value = 0
			self.FAN.cputemp.value = 0
			self.FAN.usealttime.value = False
		if mode == "off" and self.FAN.hddwatch.value != "none":
			if not self.internal_hdd:
				self.session.open(MessageBox, _("You may not use this mode!\nNot found an internal hard drive!"), MessageBox.TYPE_INFO, timeout=5)
				self.FAN.hddwatch.value = "none"
				self.FAN.hddsleep.value = False
				self.FAN.hddtemp.value = 0
				self.createSetup()
				return
		if self.FAN.timeset.value != "none" and self.FAN.timestartoff.value == self.FAN.timeendoff.value:
			self.session.open(MessageBox, _("Start time equal end time.\nYou may not use this time settings!"), MessageBox.TYPE_INFO, timeout=5)
			self.FAN.timeset.value = "none"
			self.createSetup()
			return
		if self.FAN.hddwatch.value == "sleep" and timehddsleep == "0" and self.FAN.hddsleep.value:
			self.session.open(MessageBox, _("Harddisk setup 'Standby after' disabled\nYou may not use this mode!"), MessageBox.TYPE_INFO, timeout=5)
			self.FAN.hddwatch.value = "none"
			self.FAN.hddsleep.value = False
			self.FAN.hddtemp.value = 0
			self.createSetup()
			return
		if self.fanspeedcontrol is not None and (self.FAN.syswatch.value != "none" or self.FAN.hddwatch.value != "none") and self.FAN.usealttime.value:
			if self.FAN.alt_timestart.value == self.FAN.alt_timeend.value:
				self.session.open(MessageBox, _("Start time equal end time.\nYou may not use this time settings!"), MessageBox.TYPE_INFO, timeout=5)
				self.FAN.usealttime.value = False
				self.createSetup()
				return
		if mode == "off":
			if self.FAN.hddwatch.value != "none":
				self.FAN.syswatch.value = "none"
				self.FAN.systemtemp.value = 0
				self.FAN.cputemp.value = 0
			elif self.FAN.syswatch.value != "none":
				self.FAN.hddwatch.value = "none"
				self.FAN.hddsleep.value = False
				self.FAN.hddtemp.value = 0
		if not os.path.exists("/usr/sbin/hddtemp"):
			self.FAN.menuhdd.value = False
		if tempwatcher and (self.prev_hdddevice != self.FAN.hdddevice.value and self.FAN.hddwatch.value == "temp") or (self.prev_interval_tempwatcher != self.FAN.interval_tempwatcher.value):
			tempwatcher.reloadHddTemp(devices=self.FAN.hdddevice.value, updatetime=int(self.FAN.interval_tempwatcher.value))
		if self.prev_menuhdd != self.FAN.menuhdd.value:
			self.refreshPlugins()
		if MODEL_NAME.startswith("et"):
			self.FAN.alt_auto.value = False
		self.FAN.save()
		configfile.save()
		if fanmanager is not None:
			fanmanager.fanModeChanged(None)
		self.close()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def keyYellow(self):
		if self.internal_hdd:
			menu = [(_("Use 'HddTempWatcher'"), "watcher"), (_("hddtemp -all"), "all"), (_("hddtemp -all and wake up"), "wakeup")]

			def hddAction(choice):
				if choice is not None:
					if choice[1] == "watcher":
						message, type = getHDDTempInfo()
						self.session.open(MessageBox, message, type=type, timeout=10)
					elif choice[1] == "all":
						 show_temp_simple(self.session)
					elif choice[1] == "wakeup":
						show_temp_simple(self.session, wakeup=True)
			self.session.openWithCallback(hddAction, ChoiceBox, list=menu)

	def refreshPlugins(self):
		from Components.PluginComponent import plugins
		plugins.clearPluginList()
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		sel = self["config"].getCurrent()
		if sel is None:
			return ""
		if sel in (self.cfg_altfanspeed, self.cfg_fanspeed, self.cfg_standbyfanspeed):
			return len(sel) > 0 and (str(sel[1].getText()) + _(" pwm")) or ""
		else:
			return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		sel = self["config"].getCurrent()
		if sel is None:
			return ""
		return len(sel) > 0 and str(sel[1].getText()) or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary


class FanManager():
	def __init__(self, session):
		self.session = session
		self.timer = eTimer()
		self.fan_speedcontrol = fan_speed
		self.system_tempsensor = system_temp
		self.cpu_tempsensor = cpu_temp
		self.isTBoardTemp = self.system_tempsensor is not None or self.cpu_tempsensor is not None
		self.timer.callback.append(self.timerPoll)
		config.plugins.extrafancontrol.mode.addNotifier(self.fanModeChanged)
		config.plugins.extrafancontrol.interval.addNotifier(self.fanModeChanged)
		if isSetPMW:
			config.plugins.extrafancontrol.fanspeed.addNotifier(self.fanModeChanged)

	def fanModeChanged(self, cfgElem=None):
		self.timer.stop()
		self.timer.start(100, True)

	def setSession(self, session=None):
		if session:
			self.session = session

	def timerPoll(self):
		FanConf = config.plugins.extrafancontrol
		self.polltime = int(FanConf.interval.value)
		timeout = self.polltime
		speed = FanConf.fanspeed.value
		is_standby_box = Standby.inStandby is not None
		standbyspeed = FanConf.speedstandby.value == "other" and is_standby_box
		mode = FanConf.mode.value
		prev_mode = mode
		timeset = FanConf.timeset.value
		hddwatch = FanConf.hddwatch.value
		syswatch = FanConf.syswatch.value
		set_altspeed = False
		# check time settings and if need change fan mode
		if mode != "off" and timeset != "none":
			altspeed = False
			ts = localtime()
			nowsec = (ts.tm_hour * 3600) + (ts.tm_min * 60)
			offlist = FanConf.timestartoff.value
			offsec = (offlist[0] * 3600) + (offlist[1] * 60)
			onlist = FanConf.timeendoff.value
			onsec = (onlist[0] * 3600) + (onlist[1] * 60)
			invert = False
			if offsec > onsec:
				invert = True
				offsec, onsec = onsec, offsec
			if (offsec <= nowsec < onsec):
				if not invert:
					mode = timeset
					altspeed = True
				timeout = min(self.polltime, onsec - nowsec)
			elif nowsec < offsec:
				if invert:
					mode = timeset
					altspeed = True
				timeout = min(self.polltime, offsec - nowsec)
			else:
				if invert:
					mode = timeset
					altspeed = True
				timeout = min(self.polltime, 86400 - nowsec)
			if FanConf.usealtfanspeed.value and altspeed:
				speed = FanConf.altfanspeed.value
			if self.fan_speedcontrol is not None and not altspeed and standbyspeed:
				speed = FanConf.standbyfanspeed.value
		# check hdd settings (sleeping or temperature hdd's)
		elif mode == "off" and hddwatch != "none":
			hddcount = harddiskmanager.HDDCount()
			if hddcount:
				hddlist = []
				hdd_device = FanConf.hdddevice.value
				for hdd in harddiskmanager.HDDList():
					if "pci" in hdd[1].phys_path or "ahci" in hdd[1].phys_path or "sata" in hdd[1].phys_path:
						if hdd_device == "all" or (hdd[1].dev_path == hdd_device):
							hddlist.append(hdd)
				internal_hdd_count = len(hddlist)
				if internal_hdd_count:
					if hddwatch == "sleep" and FanConf.hddsleep.value:
						sleepcount = 0
						for x in hddlist:
							if isSleepStateDevice(x[1].dev_path) is True:
								sleepcount += 1
							else:
								mode = "on"
								set_altspeed = True
						if sleepcount == internal_hdd_count:
							mode = "off"
							set_altspeed = False
					elif hddwatch == "temp" and FanConf.hddtemp.value != 0:
						hdd_temp_list = tempwatcher.getHddTempList()
						found_hdd = False
						for x in hddlist:
							for d in hdd_temp_list:
								hddtemp = hdd_temp_list[d]["temp"]
								hddpath = hdd_temp_list[d]["path"]
								if hdd_device == "all" or (hddpath == x[1].dev_path):
									found_hdd = True
									if hddtemp >= FanConf.hddtemp.value:
										mode = "on"
										set_altspeed = True
									else:
										mode = "off"
										set_altspeed = False
						if not found_hdd:
							mode = "off"
							set_altspeed = False
					else:
						timeout = 180
				else:
					timeout = 180
			else:
				timeout = 180
		# check board temperature (cpu silicon or system)
		elif mode == "off" and syswatch != "none":
			if self.system_tempsensor is not None and syswatch == "system" and FanConf.systemtemp.value != 0:
				temp = getSystemTemp()
				if temp is not None:
					if temp >= FanConf.systemtemp.value:
						mode = "on"
						set_altspeed = True
						# adjust speed:
						# - use initial speed when current sys temp > user specified value
						# - increase speed til max. Max is reached when current sys temp = 2 * user specified value
						#speed = min(FanConf.fanspeed.value + (255 - FanConf.fanspeed.value) * ((temp / FanConf.systemtemp.value) - 1), 255)
			elif self.cpu_tempsensor is not None and syswatch == "cpu" and FanConf.cputemp.value != 0:
				temp = getCPUtemp()
				if temp is not None:
					if temp >= FanConf.cputemp.value:
						mode = "on"
						set_altspeed = True
		else:
			timeout = 180
		need_setspeed = False
		if FanConf.usealttime.value and set_altspeed:
			ts = localtime()
			nowsec = (ts.tm_hour * 3600) + (ts.tm_min * 60)
			offlist = FanConf.alt_timestart.value
			offsec = (offlist[0] * 3600) + (offlist[1] * 60)
			onlist = FanConf.alt_timeend.value
			onsec = (onlist[0] * 3600) + (onlist[1] * 60)
			invert = False
			if offsec > onsec:
				invert = True
				offsec, onsec = onsec, offsec
			if (offsec <= nowsec < onsec):
				if not invert:
					need_setspeed = True
			elif nowsec < offsec:
				if invert:
					need_setspeed = True
			else:
				if invert:
					need_setspeed = True
			if need_setspeed:
				speed = FanConf.altfanspeed.value
		if self.fan_speedcontrol is not None and prev_mode == "off" and (hddwatch != "none" or syswatch != "none"):
			if not need_setspeed and set_altspeed and standbyspeed:
				speed = FanConf.standbyfanspeed.value
		if mode == "standby":
			if is_standby_box:
				self.applySettings("off", 0)
			else:
				self.applySettings("on", speed)
		else:
			if mode == "auto" and FanConf.alt_auto.value:
				if is_standby_box:
					if self.session.nav.getRecordings():
						mode = "on"
					else:
						mode = "off"
				else:
					mode = "on"
			self.applySettings(mode, speed)
		self.timer.start(timeout * 1000, True)

	def applySettings(self, mode, speed):
		try:
			file = open("/proc/stb/fp/fan", "w")
			file.write('%s' % mode)
			file.close()
		except:
			pass
		try:
			if speed > 255:
				return
			file = open("/proc/stb/fp/fan_pwm", "w")
			file.write(hex(speed)[2:])
			file.close()
		except:
			pass


def getSystemTemp():
	try:
		temp = None
		if os.path.exists('/proc/stb/sensors/temp/value'):
			fd = open('/proc/stb/sensors/temp/value', 'r')
			temp = int(fd.read().strip(), 0)
			fd.close()
		elif os.path.exists('/proc/stb/fp/temp_sensor'):
			fd = open('/proc/stb/fp/temp_sensor', 'r')
			temp = int(fd.read().strip(), 0)
			fd.close()
		return temp
	except:
		return None


def getCPUtemp():
	try:
		fd = open('/proc/stb/fp/temp_sensor_avs', 'r')
		temp = int(fd.read().strip(), 0)
		fd.close()
		return temp
	except:
		return None


def getPWM():
	try:
		f = open("/proc/stb/fp/fan_pwm", "r")
		value = int(f.readline().strip(), 16)
		f.close()
		return value
	except:
		return None


def getHDDTempInfo(all=False):
	if not os.path.exists("/usr/sbin/hddtemp"):
		return _("HDDtemp not installed!"), MessageBox.TYPE_ERROR
	if tempwatcher is None:
		return _("HddTempWatcher not running!"), MessageBox.TYPE_ERROR
	internal_hddlist = []
	internal = False
	for hdd in harddiskmanager.HDDList():
		if "pci" in hdd[1].phys_path or "ahci" in hdd[1].phys_path or "sata" in hdd[1].phys_path:
			internal_hddlist.append(hdd[1].getDeviceDir())
			internal = True
	message = ""
	hddlist = tempwatcher.getHddTempList()
	add_message = _("Try adding your internal HDD/SSD in '/usr/share/misc/hddtemp.db' manually (for SSD use 190 value).")
	for d in hddlist:
		if d in internal_hddlist:
			message += "%s %s\n" % (hddlist[d]["path"], hddlist[d]["name"])
			if hddlist[d]["temp"] == -253:
				message += _("Drive is sleeping\n")
			elif hddlist[d]["temp"] == -254:
				message += _("ERROR\n")
			elif hddlist[d]["temp"] == -255:
				message += _("unknown\n")
			else:
				answer = "%s%s" % (hddlist[d]["temp"], hddlist[d]["unit"])
				if answer == "":
					message += add_message
				else:
					message += _("temp: ") + "%s %s\n" % (hddlist[d]["temp"], hddlist[d]["unit"])
	if message == "" and not internal:
		message = _("Not found an internal HDD/SSD!\n\n")
	elif message == "" and internal:
		message = _("ERROR\n") + add_message
	elif message != "":
		message = _("Found internal HDD/SSD!\n") + "\n" + message
	if all and system_temp:
		temp = getSystemTemp()
		if temp is not None:
			message += _("\nSystem temperature: ") + str(temp) + str('\xc2\xb0') + ' C'
	if all and cpu_temp:
		cputemp = getCPUtemp()
		if cputemp is not None:
			message += _("\nCPU temperature: ") + str(cputemp) + str('\xc2\xb0') + ' C'
	return message, MessageBox.TYPE_INFO


def isSleepStateDevice(device):
	ret = os.popen("hdparm -C %s" % device).read()
	if 'SG_IO' in ret or 'HDIO_DRIVE_CMD' in ret:
		return None
	if 'drive state is:  standby' in ret or 'drive state is:  idle' in ret:
		return True
	elif 'drive state is:  active/idle' in ret:
		return False
	return None


def show_temp(session, **kwargs):
	message, type = getHDDTempInfo(True)
	session.open(MessageBox, message, type=type)


def show_temp_simple(session, wakeup=False, **kwargs):
	if not os.path.exists("/usr/sbin/hddtemp"):
		session.open(MessageBox, _("HDDtemp not installed!"), type=MessageBox.TYPE_ERROR, timeout=5)
		return
	internal_hddlist = []
	ret = ""
	arg = ""
	if wakeup:
		arg = "-w"
	for hdd in harddiskmanager.HDDList():
		if "pci" in hdd[1].phys_path or "ahci" in hdd[1].phys_path or "sata" in hdd[1].phys_path:
			internal_hddlist.append(hdd[1].getDeviceDir())
			ret += os.popen("hddtemp %s %s" % (arg, hdd[1].getDeviceDir())).read()
			if not ret and not arg:
				try:
					ret = hdd[1].model() + " " + "drive is sleeping"
				except:
					pass
			ret += "\n"
	if internal_hddlist:
		message = _("Found internal HDD/SSD!\n") + "\n" + ret
		session.open(MessageBox, message, type=MessageBox.TYPE_INFO)
	else:
		session.open(MessageBox, _("Not found an internal HDD/SSD!\n\n"), type=MessageBox.TYPE_INFO, timeout=5)


def main(session, **kwargs):
	session.open(ExtraFanControlScreen)


def startupwatcher(reason, **kwargs):
	if reason == 0 and "session" in kwargs:
		global tempwatcher, fanmanager
		if tempwatcher is None:
			tempwatcher = HddTempWatcher(devices=config.plugins.extrafancontrol.hdddevice.value, updatetime=int(config.plugins.extrafancontrol.interval_tempwatcher.value))
		session = kwargs["session"]
		if fanmanager is None and session:
			fanmanager = FanManager(session)


def openSetup(menuid, **kwargs):
	if menuid == "system":
		return [(_("Extra fan control"), main, "extrafansetup_config", 70)]
	return []


def Plugins(**kwargs):
	if fan_mode:
		lst = [PluginDescriptor(name="Extra fan control", where=PluginDescriptor.WHERE_MENU, needsRestart=True, fnc=openSetup),
			PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc=startupwatcher)]
		if config.plugins.extrafancontrol.menuhdd.value:
			lst.append(PluginDescriptor(name=_("Show HDD/SSD temp"), where=[PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=show_temp))
		return lst
	else:
		return [PluginDescriptor(name=_("Show HDD/SSD temp"), where=[PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=show_temp_simple)]
	return []
