#   Copyright 2015 Scott Bezek
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import re
import xml
from xml.dom import minidom

"""
Processes SVG files generated by pcbnew to colorize and merge
"""

logger = logging.getLogger(__name__)

class SvgProcessor(object):

    def __init__(self, input_file):
        self.dom = minidom.parse(input_file)
        self.svg_node = self.dom.documentElement

    def apply_color_transform(self, transform_function):
        # Set fill and stroke on all groups
        for group in self.svg_node.getElementsByTagName('g'):
            SvgProcessor._apply_transform(group, {
                'fill': transform_function,
                'stroke': transform_function,
            })

    def import_groups(self, from_svg_processor):
        for child in from_svg_processor.svg_node.childNodes:
            if child.nodeType != child.ELEMENT_NODE:
                continue
            if child.tagName == 'defs':
                self.svg_node.appendChild(self.dom.importNode(child, True))
                continue
            if child.tagName != 'g':
                continue
            group = child
            output_node = self.dom.importNode(group, True)
            self.svg_node.appendChild(output_node)

    def write(self, filename):
        with open(filename, 'wb') as output_file:
            self.svg_node.writexml(output_file)

    def wrap_with_group(self, attrs):
        parent = self.svg_node
        wrapper = self.dom.createElement("g")
        for k,v in attrs.items():
            wrapper.setAttribute(k,v)

        for child in parent.getElementsByTagName('g'):
            parent.removeChild(child)
            wrapper.appendChild(child)

        parent.appendChild(wrapper)

    def Invert(self, colour, opacity):
        parent = self.svg_node
        wrapper = self.dom.createElement("mask")
        MaskGroup = self.dom.createElement("g")

        # Save Bounding Rectangle easy hack it's the 3rd item...
        bounding_rect =  parent.getElementsByTagName('g')[2].getElementsByTagName("rect")[0]

        #print bounding_rect.toxml()


        height = bounding_rect.attributes['height'].value
        width = bounding_rect.attributes['width'].value
        x = bounding_rect.attributes['x'].value
        y = bounding_rect.attributes['y'].value
            
        wrapper.setAttribute('id', 'mask-a')
        wrapper.setAttribute('height', height)
        wrapper.setAttribute('width', width)
        wrapper.setAttribute('x', x)
        wrapper.setAttribute('y', y)

        for child in parent.getElementsByTagName('g'):
            parent.removeChild(child)
            MaskGroup.appendChild(child)

        wrapper.appendChild(MaskGroup)

        def_wrapper = self.dom.createElement("defs")
        def_wrapper.appendChild(wrapper);

        parent.appendChild(def_wrapper)

        #create a group to mask from
        mask_group = self.dom.createElement("g")

        mask_group.setAttribute('style', 'fill:' + colour + '; fill-opacity:' + str(opacity) + '; mask: url(#mask-a);')
        mask_group.appendChild(bounding_rect.cloneNode(deep=True))

        parent.appendChild(mask_group)


    @staticmethod
    def _apply_transform(node, values):
        original_style = node.attributes['style'].value
        for (k,v) in values.items():
            escaped_key = re.escape(k)
            m = re.search(r'\b' + escaped_key + r':(?P<value>[^;]*);', original_style)
            if m:
                transformed_value = v(m.group('value'))
                original_style = re.sub(
                    r'\b' + escaped_key + r':[^;]*;',
                    k + ':' + transformed_value + ';',
                    original_style)
        node.attributes['style'] = original_style