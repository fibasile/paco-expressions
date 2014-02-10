import os
import sys
import logging
import tempfile
import codecs

USE_WAND=True
INKSCAPE_EXTENSIONS_PATH='/usr/share/inkscape/extensions/'
INKSCAPE_PATH='/usr/bin/inkscape'
CONVERT_PATH='/usr/bin/convert'
env = os.environ
    
# my_env = os.environ
    
if sys.platform == 'darwin':
    INKSCAPE_EXTENSIONS_PATH='/Applications/Inkscape.app/Contents/Resources/extensions/'
    INKSCAPE_PATH='/Applications/Inkscape.app/Contents/Resources/bin/inkscape'
    CONVERT_PATH='convert'
    env['MAGIC_HOME']='/usr/local/lib'
try:
    from subprocess import Popen, PIPE
    bsubprocess = True
except:
    bsubprocess = False
    
try:
    import xml.etree.ElementTree as et
except ImportError, e:
    try:
        from lxml import etree as et
    except:
        sys.exit(_('The fantastic lxml wrapper for libxml2 is required by inkex.py and therefore this extension. Please download and install the latest version from http://cheeseshop.python.org/pypi/lxml/, or install it through your package manager by a command like: sudo apt-get install python-lxml'))

sys.path.append(INKSCAPE_EXTENSIONS_PATH)



import inkex
import simplestyle

logging.basicConfig(filename=os.path.join(tempfile.gettempdir(), 'inklog.log'), level=logging.DEBUG)



class ExportExpressions(inkex.Effect):
    """Exports all layers as an xbm file via gimp"""
    def __init__(self):
        inkex.Effect.__init__(self)
        self.temp_svg_file = tempfile.NamedTemporaryFile(suffix='.svg',delete=False)
        self.color_map = {} # change color based on overwrite
                            # green - new export
                            # red - overwrite
                            # grey - not exported (no overwrite)
        self.OptionParser.add_option("--tab",
                                     action="store", type="string", 
                                     dest="tab", default="sampling",
                                     help="The selected UI-tab when OK was pressed")
        self.OptionParser.add_option("-d", "--directory",
                                     action="store", type="string", 
                                     dest="directory", default=os.path.expanduser("~"),
                                     help="Existing destination directory")
        self.OptionParser.add_option("", "--size_width",
                                     action="store", type="string",
                                     dest="size_width", default="128",
                                     help="width to export")
        self.OptionParser.add_option("", "--size_height",
                                     action="store", type="string",
                                     dest="size_height", default="64",
                                     help="height to export")
        self.OptionParser.add_option("-o", "--overwrite",
                                     action="store", type="inkbool", default=True,
                                     help="Overwrite existing exports?")
                                     
    def effect(self):
        if not os.path.isdir(self.options.directory):
                    os.makedirs(self.options.directory)
        self.save_temp_svg()
        
        layers = self.enum_layers()
        area = []
        for node in layers:
            label_value = node.attrib.get('{http://www.inkscape.org/namespaces/inkscape}label', None)
            if label_value == 'Frame':
                area = self.extract_area(node)
                
        for node in layers:
            label_value = node.attrib.get('{http://www.inkscape.org/namespaces/inkscape}label', None)
            # print 'Found layer %s' % label_value
            if label_value != 'Frame':
                # print 'Exporting layer id %s' % node.attrib["id"]
                png_filename = '%s.png' % label_value
                xbm_filename = '%s.xbm' % label_value
                self.export_node(node,png_filename, self.options.size_width, self.options.size_height, area)
                self.convert_xbm(png_filename , xbm_filename)
                self.cleanup(png_filename)
        # self.cleanup(self.temp_svg_file.name)

    def save_temp_svg(self):
        svg = codecs.open(self.args[-1],'r')
        self.temp_svg_file.write(svg.read())
        svg.close()
        self.temp_svg_file.close()

                
    def cleanup(self,pathname):
        directory = self.options.directory
        filename = os.path.join(directory, pathname)
        os.remove(filename)
        
        
    def extract_area(self,node):
        rect = node.findall('{http://www.w3.org/2000/svg}rect')[0]
        area = (rect.attrib['x'],rect.attrib['y'],rect.attrib['width'],rect.attrib['height'])
        return area
        
        
    def enum_layers(self):
        return self.document.findall('{http://www.w3.org/2000/svg}g')
        
    def convert_xbm(self, in_file_name, out_file_name):
        directory = self.options.directory
        in_filename = os.path.join(directory, in_file_name)
        out_filename = os.path.join(directory, out_file_name)
        if self.options.overwrite or not os.path.exists(in_filename):
            if USE_WAND:
                from wand.image import Image
                with Image(filename=in_filename) as img:
                    img.format = 'xbm'
                    img.save(filename=out_filename)
            else:
                command = "%s %s %s" % (CONVERT_PATH, in_filename, out_filename)
                # print command
                if bsubprocess:
                    p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE,env=env)
                    return_code = p.wait()
                    f = p.stdout
                    err = p.stderr
                
                    logging.log(logging.DEBUG, "COMMAND %s returned %d %s %s" % (command,return_code,f.read(), err.read()))
                else:
                    _, f, err = os.open3(command)
                logging.log(logging.DEBUG, "COMMAND %s" % command)
                f.close()
        else:
            logging.log(logging.DEBUG, "Export exists (%s) not overwriting" % out_filename)
            
            
    def export_node(self, node, file_name, width, height,area):
            """
            Eating the stderr, so it doesn't show up in a error box after
            running the script.
            """
            svg_file = self.temp_svg_file.name #self.args[-1]
            node_id = node.attrib['id']
            directory = self.options.directory
            filename = os.path.join(directory, file_name)
            #area_string = '%f:%f:%f:%f' % ( float(area[0]), float(area[1]), float(area[0]) + float(area[2]), float(area[1]) + float(area[3]))
            if self.options.overwrite or not os.path.exists(filename):
                command = "%s -z -i %s -j -D -e %s %s -h %s -w %s" % (INKSCAPE_PATH, node_id, filename, svg_file, height, width)
                # print command
                if bsubprocess:
                    p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
                    return_code = p.wait()
                    f = p.stdout
                    err = p.stderr
                    logging.log(logging.DEBUG, "COMMAND %s returned %d %s %s" % (command,return_code,f.read(), err.read()))
                else:
                    _, f, err = os.open3(command)
                    logging.log(logging.DEBUG, " Error COMMAND %s" % (command,err))
                f.close()
            else:
                logging.log(logging.DEBUG, "Export exists (%s) not overwriting" % filename)
            
def _main():
    """
    Normal flow is something like this:
      * subclass inkex.Effect
      * call affect() which:
        * provides current (svg) image in tmp file (sys.args[-1])
        * reads it into self.document (etree)
        * modifies in self.effect()
        * spits out errors to stderr
        * spits out result/new image to stdout
    """
    e = ExportExpressions()
    e.affect()
    
if __name__ == "__main__":
    _main()