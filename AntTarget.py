import sublime
import sublime_plugin
import urllib
from xml.dom import minidom
import subprocess
import functools
import threading


def main_thread(callback, *args, **kwargs):
    sublime.set_timeout(functools.partial(callback, *args, **kwargs), 0)


class CommandBase():
    def run_command(self, command):
        thread = ExternalCommandThread(command, self.generic_done)
        thread.start()

    def generic_done(self, result):
        print result


class WindowCommandBase(CommandBase):
    def panel(self, output, **kwargs):
        if not hasattr(self, 'output_view'):
            self.output_view = self.get_window().get_output_panel("ant")

        self.output_view.set_read_only(False)
        self._output_to_view(self.output_view, output, clear=True, **kwargs)
        self.output_view.set_read_only(True)
        self.get_window().run_command("show_panel", {"panel": "output.ant"})

    def quick_panel(self, *args, **kwargs):
        self.get_window().show_quick_panel(*args, **kwargs)

    def get_window(self):
        return self.window


class AntTargetCommand(sublime_plugin.TextCommand):

    def __init__(self, view):
        self.view = view
        self.window = self.view.window()
        self.buildFilePath = 'build/build.xml'
        self.projectPath = self.window.folders()[0]

    def run(self, edit):
        self.printProjectInfo()
        self.parseBuildFile(self.projectPath + '/' + self.buildFilePath)

    def printProjectInfo(self):
        print '----------'
        print 'buildFilePath: ' + self.buildFilePath
        print 'projectPath: ' + self.projectPath
        print '--'

    def parseBuildFile(self, filePath):
        dom = minidom.parse(urllib.urlopen(filePath))
        targets = dom.getElementsByTagName("target")
        #print 'Found %i targets:' % targets.length
        #call(["ant", "default"])
        buildCommand = "ant -buildfile %s Default" % filePath
        for index in range(len(targets)):
            print '%i) Target: %s' % (index, targets[index].attributes['name'].value)

        print ''
        thread = ExternalCommandThread(buildCommand, self.generic_done)
        thread.start()

    def generic_done(self, result):
        print result


class AntShowTargetsCommand(WindowCommandBase, sublime_plugin.WindowCommand):

    def run(self):
        self.buildFilePath = 'build/build.xml'
        self.projectPath = self.window.folders()[0]
        self.results = []
        dom = minidom.parse(urllib.urlopen(self.projectPath + '/' + self.buildFilePath))
        targets = dom.getElementsByTagName("target")
        for index in range(len(targets)):
            #target = '%i Target: %s' % (index, targets[index].attributes['name'].value)
            target = targets[index].attributes['name'].value
            description = targets[index].getAttribute('description') or '[no description]'
            self.results.insert(index, [target, description])

        self.quick_panel(self.results, self.panel_done)
        sublime.status_message('Listed targets')

    def generic_done(self, result):
        print result

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        item = self.results[picked]
        ref = item[0]
        buildCommand = "ant -buildfile %s %s" % (self.projectPath + '/' + self.buildFilePath, ref)
        print '- - - - - \n\n'
        self.run_command(buildCommand)


class ExternalCommandThread(threading.Thread):
    def __init__(self, command, on_done):
        threading.Thread.__init__(self)
        self.command = command
        self.on_done = on_done

    def run(self):
        proc = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
        output = proc.communicate()[0]
        # if sublime's python gets bumped to 2.7 we can just do:
        # output = subprocess.check_output(self.command)
        main_thread(self.on_done, output.decode('utf-8'))
