from lxml import etree
from requests import Response


def treeify_xml(response: Response):
    xml_content = response.text.encode('utf-8')
    parser = etree.XMLParser(ns_clean=True, recover=True)
    return etree.fromstring(bytes(xml_content), parser=parser)
