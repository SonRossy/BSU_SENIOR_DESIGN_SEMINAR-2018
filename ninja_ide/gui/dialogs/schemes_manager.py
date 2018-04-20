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

from __future__ import absolute_import

import webbrowser

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QSpacerItem,
    QPushButton,
    QLabel
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import (
    Qt,
    QSize
)

import ninja_ide
from ninja_ide import translations


class SchemesManagerWidget(QDialog):

    def __init__(self, parent=None):
        QDialog.__init__(self, parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setWindowTitle(self.tr("SCHEMES"))
        self.setMaximumSize(QSize(0, 0))

        vbox = QVBoxLayout(self)

        # Create an icon for the Dialog
        pixmap = QPixmap(":img/icon")
        self.lblIcon = QLabel()
        self.lblIcon.setPixmap(pixmap)

        hbox = QHBoxLayout()
        hbox.addWidget(self.lblIcon)

        lblTitle = QLabel(
                '<h1>NINJA-SCHEMES</h1>\n<i>Ninja-IDE Is Not Just Another IDE<i>')
        lblTitle.setTextFormat(Qt.RichText)
        lblTitle.setAlignment(Qt.AlignLeft)
        hbox.addWidget(lblTitle)
        vbox.addLayout(hbox)
        # Add description
        vbox.addWidget(QLabel(
self.tr("""NINJA-IDE (from: "Ninja Is Not Just Another IDE"), We're currently working on several color schemes. 
    However please see the list of schemes we have available (classic_ninja, coder, buntu_new etc.).
""")))
        vbox.addWidget(QLabel(self.tr("Version: %s") % ninja_ide.__version__))
        link_schemes = QLabel(
            self.tr('Website: <a href="%s"><span style=" '
                'text-decoration: underline; color:#ff9e21;">'
                '%s</span></a>') %
                (ninja_ide.__schemes__, ninja_ide.__schemes__))
        vbox.addWidget(link_schemes)
        

        hbox2 = QHBoxLayout()
        hbox2.addSpacerItem(QSpacerItem(1, 0, QSizePolicy.Expanding))
        btn_close = QPushButton(translations.TR_CLOSE)
        hbox2.addWidget(btn_close)
        vbox.addLayout(hbox2)

        # FIXME: setOpenExternalLinks on labels
        link_schemes.linkActivated['QString'].connect(self.link_activated)
        btn_close.clicked.connect(self.close)

    def link_activated(self, link):
        webbrowser.open(str(link))
