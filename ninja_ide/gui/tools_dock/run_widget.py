# -*- coding: utf-8 -*-
#
# This file is part of NINJA-IDE (http://ninja-ide.org).
#
# NINJA-IDE is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# any later version.
#
# NINJA-IDE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NINJA-IDE; If not, see <http://www.gnu.org/licenses/>.

import re
import os
import subprocess
from subprocess import Popen, PIPE
import time

from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QMenu


from PyQt5.QtGui import QColor
from PyQt5.QtGui import QTextCharFormat
from PyQt5.QtGui import QTextCursor
from PyQt5.QtGui import QTextBlockFormat

from PyQt5.QtCore import Qt
from PyQt5.QtCore import QFile
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QProcess
from PyQt5.QtCore import QProcessEnvironment
from PyQt5.QtCore import QTime

from ninja_ide import translations
from ninja_ide import resources
from ninja_ide.core import settings
from ninja_ide.core.file_handling import file_manager
from ninja_ide.gui.ide import IDE
from ninja_ide.gui.tools_dock.tools_dock import _ToolsDock


# FIXME: tool buttons (clear, stop, re-start, etc)
# FIXME: maybe improve the user input


class Program(QObject):

    def __init__(self, **kwargs):
        QObject.__init__(self)
        self.filename = kwargs.get("filename")
        self.text_code = kwargs.get("code")
        self.__python_exec = kwargs.get("python_exec")
        self.pre_script = kwargs.get("pre_script")
        self.post_script = kwargs.get("post_script")
        self.__params = kwargs.get("params")

        self.outputw = None

        self.__current_process = None

        self.main_process = QProcess(self)
        self.main_process.started.connect(self._process_started)
        self.main_process.finished.connect(self._process_finished)
        self.main_process.finished.connect(self.__post_execution)
        self.main_process.readyReadStandardOutput.connect(self._refresh_output)
        self.main_process.readyReadStandardError.connect(self._refresh_error)

        self.pre_process = QProcess(self)
        self.pre_process.started.connect(self._process_started)
        self.pre_process.finished.connect(self._process_finished)
        self.pre_process.finished.connect(self.__main_execution)
        self.pre_process.readyReadStandardOutput.connect(self._refresh_output)
        self.pre_process.readyReadStandardError.connect(self._refresh_error)

        self.post_process = QProcess(self)
        self.post_process.started.connect(self._process_started)
        self.post_process.finished.connect(self._process_finished)
        self.post_process.readyReadStandardOutput.connect(self._refresh_output)
        self.post_process.readyReadStandardError.connect(self._refresh_error)

    def start(self):
        self.__pre_execution()
        self.outputw.setFocus()

    def __pre_execution(self):
        """Execute a script before executing the project"""
        self.__current_process = self.pre_process
        file_pre_exec = QFile(self.pre_script)
        if file_pre_exec.exists():
            ext = file_manager.get_file_extension(self.pre_script)
            args = []
            if ext == "py":
                program = self.python_exec
                # -u: Force python to unbuffer stding ad stdout
                args.append("-u")
                args.append(self.pre_script)
            elif ext == "sh":
                program = "bash"
                args.append(self.pre_script)
            else:
                program = self.pre_script
            self.pre_process.setProgram(program)
            self.pre_process.setArguments(args)
            self.pre_process.start()
        else:
            self.__main_execution()

    def __main_execution(self):
        self.__current_process = self.main_process
        if not self.only_text:
            # In case a text is executed and not a file or project
            file_directory = file_manager.get_folder(self.filename)
            self.main_process.setWorkingDirectory(file_directory)
        self.main_process.setProgram(self.python_exec)
        self.main_process.setArguments(self.arguments)
        environment = QProcessEnvironment()
        system_environment = self.main_process.systemEnvironment()
        for env in system_environment:
            key, value = env.split("=", 1)
            environment.insert(key, value)
        self.main_process.setProcessEnvironment(environment)
        self.main_process.start()

    def __post_execution(self):
        """Execute a script after executing the project."""
        self.__current_process = self.post_process
        file_pre_exec = QFile(self.post_script)
        if file_pre_exec.exists():
            ext = file_manager.get_file_extension(self.post_script)
            args = []
            if ext == "py":
                program = self.python_exec
                # -u: Force python to unbuffer stding ad stdout
                args.append("-u")
                args.append(self.post_script)
            elif ext == "sh":
                program = "bash"
                args.append(self.post_script)
            else:
                program = self.post_script
            self.post_process.setProgram(program)
            self.post_process.setArguments(args)
            self.post_process.start()

    @property
    def process_name(self):
        proc = self.__current_process
        return proc.program() + " " + " ".join(proc.arguments())

    def update(self, **kwargs):
        self.text_code = kwargs.get("code")
        self.__python_exec = kwargs.get("python_exec")
        self.pre_script = kwargs.get("pre_script")
        self.post_script = kwargs.get("post_script")
        self.__params = kwargs.get("params")

    def set_output_widget(self, ow):
        self.outputw = ow
        self.outputw.inputRequested.connect(self._write_input)

    def _write_input(self, data):
        self.main_process.write(data.encode())
        self.main_process.write(b"\n")

    def is_running(self):
        running = False
        if self.main_process.state() == QProcess.Running:
            running = True
        return running

    def _process_started(self):
        time_str = QTime.currentTime().toString("hh:mm:ss")
        text = time_str + " Running: " + self.process_name
        self.outputw.append_text(text)
        self.outputw.setReadOnly(False)

    def _process_finished(self, code, status):
        # frmt = "plain"
        if status == QProcess.NormalExit == code:
            text = translations.TR_PROCESS_EXITED_NORMALLY % code
        else:
            text = translations.TR_PROCESS_INTERRUPTED
            # frmt = "error"
        self.outputw.append_text(text)
        self.outputw.setReadOnly(True)

    def _refresh_output(self):
        data = self.__current_process.readAllStandardOutput().data().decode()
        for line in data.splitlines():
            self.outputw.append_text(
                line, text_format=OutputWidget.Format.NORMAL)

    def _refresh_error(self):
        data = self.__current_process.readAllStandardError().data().decode()
        for line_text in data.splitlines():
            frmt = OutputWidget.Format.ERROR
            if self.outputw.patLink.match(line_text):
                frmt = OutputWidget.Format.ERROR_UNDERLINE
            self.outputw.append_text(line_text, frmt)

    def display_name(self):
        name = "New document"
        if not self.only_text:
            name = file_manager.get_basename(self.filename)
        return name

    @property
    def only_text(self):
        return self.filename is None

    @property
    def python_exec(self):
        py_exec = self.__python_exec
        if not py_exec:
            py_exec = settings.PYTHON_EXEC
        return py_exec

    @property
    def arguments(self):
        args = []
        if self.text_code:
            args.append("-c")
            args.append(self.text_code)
        else:
            # Force python to unbuffer stding and stdout
            args.append("-u")
            args += settings.EXECUTION_OPTIONS.split()
            args.append(self.filename)
        return args


class RunWidget(QWidget):

    allTabsClosed = pyqtSignal()
    projectExecuted = pyqtSignal("QString")

    def __init__(self):
        QWidget.__init__(self)
        self.__programs = []

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        connections = (
            {
                "target": "tools_dock",
                "signal_name": "executeFile",
                "slot": self.execute_file
            },
            {
                "target": "tools_dock",
                "signal_name": "executeProject",
                "slot": self.execute_project
            },
            {
                "target": "tools_dock",
                "signal_name": "executeSelection",
                "slot": self.execute_selection
            }
        )
        IDE.register_signals("tools_dock", connections)

        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)
        vbox.addWidget(self._tabs)
        # Menu for tab
        self._tabs.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self._tabs.tabBar().customContextMenuRequested.connect(
            self._menu_for_tabbar)
        self._tabs.tabCloseRequested.connect(self.close_tab)

        IDE.register_service("run_widget", self)
        _ToolsDock.register_widget(translations.TR_OUTPUT, self)

    def install(self):
        pass

    def _menu_for_tabbar(self, position):
        menu = QMenu()
        close_action = menu.addAction(translations.TR_CLOSE_TAB)
        close_all_action = menu.addAction(translations.TR_CLOSE_ALL_TABS)
        close_other_action = menu.addAction(translations.TR_CLOSE_OTHER_TABS)

        qaction = menu.exec_(self.mapToGlobal(position))

        if qaction == close_action:
            index = self._tabs.tabBar().tabAt(position)
            self.close_tab(index)
        elif qaction == close_all_action:
            self.close_all_tabs()
        elif qaction == close_other_action:
            self.close_all_tabs_except_this()

    def close_tab(self, tab_index):
        program = self.__programs[tab_index]
        self.__programs.remove(program)
        self._tabs.removeTab(tab_index)
        # Close process and delete OutputWidget
        program.main_process.close()
        #program.outputw.deleteLater()
        del program.outputw

        if self._tabs.count() == 0:
            # Hide widget
            self.allTabsClosed.emit()

    def close_all_tabs(self):
        for _ in range(self._tabs.count()):
            self.close_tab(0)

    def close_all_tabs_except_this(self):
        self._tabs.tabBar().moveTab(self._tabs.currentIndex(), 0)
        for _ in range(self._tabs.count()):
            if self._tabs.count() > 1:
                self.close_tab(1)

    def execute_file(self):
        """Execute the current file"""
        main_container = IDE.get_service("main_container")
        editor_widget = main_container.get_current_editor()
        if editor_widget is not None and (editor_widget.is_modified or
                                          editor_widget.file_path):
            main_container.save_file(editor_widget)
            # FIXME: Emit a signal for plugin!
            # self.fileExecuted.emit(editor_widget.file_path)
            file_path = editor_widget.file_path
            extension = file_manager.get_file_extension(file_path)
            # TODO: Remove the IF statment and use Handlers
            if extension == "py":
                self.start_process(filename=file_path)
            elif extension =="java":
                if os.name=='posix':
                    self.RunMacJavaProgram(file_path)#thats where my code starts see the RunJavProgram Function below
                elif os.name=='nt':
                    self.runWindowsJavaProgram(file_path)

            '''# Run .c file
            # added this module
            if extension == "c":
            	self.start_process(filename=file_path)'''
    def runWindowsJavaProgram(self,file_path):
        from subprocess import Popen, CREATE_NEW_CONSOLE
        CompileProgramCommand="javac "+file_path
        file_path2=""
        path=file_manager.get_file_name(file_path)#getting the path
        new_path=file_manager.get_file_name(file_path)#getting the path
        new_path=new_path.split('/')#getting just the filename from the path
        print(new_path)
        file_name=new_path[len(new_path)-1]#the last item string in the list i created above is the file name
        for i in range(0,len(new_path)-1):
           file_path2=file_path2+'/'+new_path[i]#recreating th path since i messed it up above
           file_path3=file_path2[1:]

        os.chdir(file_path3)#pointing os to our directory in order to find files

        if os.path.isfile(path+'.class'):
            os.remove(path+'.class')#if file was previously compiled then we delete so we can recompile
        procToCompile = subprocess.Popen(CompileProgramCommand,stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
        out,err=procToCompile.communicate()
        runProgramCommand="java "#+file_name# command to run java code
        javaProgram=Program()#created a program object, check Program class, the next two lines prvent the program from breaking
                    #when we close a tab
        self.__programs.append(javaProgram)
        index = self.__programs.index(javaProgram)
        error=err.decode("utf-8")#in case we couldnt compile then we output the error to user
        outputw = OutputWidget(error)
        self.add_tab(outputw, "java")#adding tab to see error
        #we running th file  if it was compile
        procToRun= subprocess.Popen([runProgramCommand, file_name], creationflags = subprocess.CREATE_NEW_CONSOLE)



    def RunMacJavaProgram(self,file_path):
        CompileProgramCommand="javac "+file_path
        file_path2=""
        path=file_manager.get_file_name(file_path)#getting the path
        new_path=file_manager.get_file_name(file_path)#getting the path
        new_path=new_path.split('/')#getting just the filename from the path
        file_name=new_path[len(new_path)-1]#the last item string in the list i created above is the file name
        for i in range(0,len(new_path)-1):
           file_path2=file_path2+'/'+new_path[i]#recreating th path since i messed it up above

        os.chdir(file_path2)#pointing os to our directory in order to find files

        if os.path.isfile(path+'.class'):
            os.remove(path+'.class')#if file was previously compiled then we delete so we can recompile
        procToCompile = subprocess.Popen(CompileProgramCommand,stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
        out,err=procToCompile.communicate()
        runProgramCommand="java "+file_name# command to run java code
        javaProgram=Program()#created a program object, check Program class, the next two lines prvent the program from breaking
                    #when we close a tab
        self.__programs.append(javaProgram)
        index = self.__programs.index(javaProgram)
        error=err.decode("utf-8")#in case we couldnt compile then we output the error to user
        outputw = OutputWidget(error)
        self.add_tab(outputw, "java")#adding tab to see error
        procToRun=subprocess.Popen(['xterm','+hold','-e',runProgramCommand])#we running th file  if it was compile


    def execute_selection(self):
        """Execute selected text or current line if not have a selection"""

        main_container = IDE.get_service("main_container")
        editor_widget = main_container.get_current_editor()
        if editor_widget is not None:
            text = editor_widget.selected_text().splitlines()
            if not text:
                # Execute current line
                text = [editor_widget.line_text()]
            code = []
            for line_text in text:
                # Get part before firs '#'
                code.append(line_text.split("#", 1)[0])
            # Join to execute with python -c command
            final_code = ";".join([line.strip() for line in code if line])
            # Highlight code to be executed
            editor_widget.show_run_cursor()
            # Ok run!
            self.start_process(
                filename=editor_widget.file_path, code=final_code)

    def execute_project(self):
        """Execute the project marked as Main Project."""

        projects_explorer = IDE.get_service("projects_explorer")
        if projects_explorer is None:
            return
        nproject = projects_explorer.current_project
        if nproject:
            main_file = nproject.main_file
            if not main_file:
                # Open project properties to specify the main file
                projects_explorer.current_tree.open_project_properties()
            else:
                # Save project files
                projects_explorer.save_project()
                # Emit a signal for plugin!
                self.projectExecuted.emit(nproject.path)

                main_file = file_manager.create_path(
                    nproject.path, nproject.main_file)
                self.start_process(
                    filename=main_file,
                    python_exec=nproject.python_exec,
                    pre_exec_script=nproject.pre_exec_script,
                    post_exec_script=nproject.post_exec_script,
                    program_params=nproject.program_params
                )

    def start_process(self, **kwargs):
        # First look if we can reuse a tab
        fname = kwargs.get("filename")
        program = None
        for prog in self.__programs:
            if prog.filename == fname:
                if not prog.is_running():
                    program = prog
                    break

        if program is not None:
            index = self.__programs.index(program)
            program.update(**kwargs)
            self._tabs.setCurrentIndex(index)
            program.outputw.gray_out_old_text()
        else:
            program = Program(**kwargs)
            # Create new output widget
            outputw = OutputWidget(self)
            program.set_output_widget(outputw)
            self.add_tab(outputw, program.display_name())
            self.__programs.append(program)

        program.start()

    def add_tab(self, outputw, tab_text):
        inserted_index = self._tabs.addTab(outputw, tab_text)
        self._tabs.setCurrentIndex(inserted_index)


class OutputWidget(QPlainTextEdit):

    """Widget to handle the output of the running process"""

    inputRequested = pyqtSignal("QString")

    class Format:
        NORMAL = "NORMAL"
        PLAIN = "PLAIN"
        ERROR = "ERROR"
        ERROR_UNDERLINE = "ERRORUNDERLINE"

    def __init__(self, parent):
        super(OutputWidget, self).__init__(parent)
        self._parent = parent
        self.setWordWrapMode(0)
        self.setMouseTracking(True)
        self.setFrameShape(0)
        self.setUndoRedoEnabled(False)
        # Traceback pattern
        self.patLink = re.compile(r'(\s)*File "(.*?)", line \d.+')
        # For user input
        self.__input = []

        self.setFont(settings.FONT)
        # Formats
        plain_format = QTextCharFormat()
        normal_format = QTextCharFormat()
        normal_format.setForeground(
            QColor(resources.COLOR_SCHEME.get("editor.foreground")))
        error_format = QTextCharFormat()
        error_format.setForeground(QColor('#ff6c6c'))
        error_format2 = QTextCharFormat()
        error_format2.setToolTip(translations.TR_CLICK_TO_SHOW_SOURCE)
        error_format2.setUnderlineStyle(QTextCharFormat.DashUnderline)
        error_format2.setForeground(QColor('#ff6c6c'))
        error_format2.setUnderlineColor(QColor('#ff6c6c'))

        self._text_formats = {
            self.Format.NORMAL: normal_format,
            self.Format.PLAIN: plain_format,
            self.Format.ERROR: error_format,
            self.Format.ERROR_UNDERLINE: error_format2
        }

        self.blockCountChanged[int].connect(
            lambda: self.moveCursor(QTextCursor.End))

        # Style
        palette = self.palette()
        palette.setColor(
            palette.Base,
            QColor(resources.COLOR_SCHEME.get('editor.background')))
        self.setPalette(palette)

    def mousePressEvent(self, event):
        """
        When the execution fail, allow to press the links in the traceback,
        to go to the line when the error occur.
        """
        QPlainTextEdit.mousePressEvent(self, event)
        self.go_to_error(event)

    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        text = cursor.block().text()
        if text:
            if self.patLink.match(text):
                self.viewport().setCursor(Qt.PointingHandCursor)
            else:
                self.viewport().setCursor(Qt.IBeamCursor)
        QPlainTextEdit.mouseMoveEvent(self, event)

    def go_to_error(self, event):
        """Resolve the link and take the user to the error line."""
        cursor = self.cursorForPosition(event.pos())
        text = cursor.block().text()
        if self.patLink.match(text):
            file_path, lineno = self._parse_traceback(text)
            main_container = IDE.get_service('main_container')
            if main_container:
                main_container.open_file(file_path, line=int(lineno) - 1)

    def _parse_traceback(self, text):
        """
        Parse a line of python traceback and returns
        a tuple with (file_name, lineno)
        """
        file_word_index = text.find('File')
        comma_min_index = text.find(',')
        # comma_max_index = text.rfind(',')
        file_name = text[file_word_index + 6:comma_min_index - 1]
        lineno = text[comma_min_index + 7:].strip()
        return (file_name, lineno)

    def append_text(self, text, text_format=None):
        cursor = self.textCursor()
        if text_format is None:
            text_format = self.Format.PLAIN
        cursor.insertText(text, self._text_formats[text_format])
        cursor.insertBlock()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y() / 120
            self.zoomIn(delta)
            return
        QPlainTextEdit.wheelEvent(self, event)

    def keyPressEvent(self, event):
        if self.isReadOnly():
            return
        modifiers = event.modifiers()
        if modifiers in (Qt.AltModifier, Qt.ControlModifier):
            return
        if modifiers == Qt.ShiftModifier:
            if not event.text():
                return
        key = event.key()
        if key == Qt.Key_Backspace:
            text_selected = self.textCursor().selectedText()
            if text_selected:
                del self.__input[-len(text_selected):]
            else:
                try:
                    self.__input.pop()
                except IndexError:
                    return
        elif key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                     Qt.Key_CapsLock):
            return
        elif key in (Qt.Key_Enter, Qt.Key_Return):
            data = "".join(self.__input)
            self.inputRequested.emit(data)
            self.__input.clear()
        else:
            self.__input.append(event.text())
        QPlainTextEdit.keyPressEvent(self, event)

    def gray_out_old_text(self):
        """Puts the old text in gray"""

        cursor = self.textCursor()
        end_format = cursor.charFormat()
        cursor.select(QTextCursor.Document)
        format_ = QTextCharFormat()
        backcolor = self.palette().base().color()
        forecolor = self.palette().text().color()
        backfactor = .5
        forefactor = 1 - backfactor
        red = backfactor * backcolor.red() + forefactor * forecolor.red()
        green = backfactor * backcolor.green() + forefactor * forecolor.green()
        blue = backfactor * backcolor.blue() + forefactor * forecolor.blue()
        format_.setForeground(QColor(red, green, blue))
        cursor.mergeCharFormat(format_)
        cursor.movePosition(QTextCursor.End)
        cursor.setCharFormat(end_format)
        cursor.insertBlock(QTextBlockFormat())


RunWidget()
