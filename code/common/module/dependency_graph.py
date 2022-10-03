import logging
from typing import List

from common.module.module import Module
from common.configuration import Configuration
from common.logging import Logging

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class DependencyNode:
    def __init__(self, name):
        self.name = name
        self.children: list = []
        self.parents: list = []
        self.loaded: bool = False


    def __str__(self):
        return "{}: {}, children: {}, parents: {}, loaded: {}".format(DependencyNode.__name__,  self.name, self.children, self.parents, self.loaded)


    def __repr__(self):
        return "{}: {}, children: {}, parents: {}, loaded: {}".format(DependencyNode.__name__,  self.name, self.children, self.parents, self.loaded)

class DependencyGraph:
    def __init__(self):
        self.roots: list = []   # list of (1 or more) root DependencyNodes that form a dependency chain
        self._node_map: dict = {}    # dictionary of class names to nodes that've been inserted into the graph
        self._orphaned_node_map: dict = {}   # dictionary of class names (that haven't been inserted into the graph) to list of nodes that require that non-existant class

    ## Methods

    def insert(self, class_name: str, dependencies = list) -> DependencyNode:
        ## Don't insert duplicates
        if (class_name in self._node_map):
            LOGGER.warn('Unable to insert {}, as it\'s already been added.'.format(class_name))
            return

        ## Build initial node & update mappings
        node = DependencyNode(class_name)
        self._node_map[class_name] = node

        ## Handle any orphaned children that depend on this class
        if (class_name in self._orphaned_node_map):
            orphaned_children = self._orphaned_node_map[class_name]

            for child in orphaned_children:
                node.children.append(child)
                child.parents.append(node)

            del self._orphaned_node_map[class_name]

        ## Process the dependencies by searching for existing nodes, otherwise populate the orphaned child map
        for dependency in dependencies:
            ## Support class or string based dependencies
            if (isinstance(dependency, str)):
                dependency_name = dependency
            else:
                dependency_name = dependency.__name__

            if (dependency_name in self._node_map):
                dependency_node = self._node_map[dependency_name]

                node.parents.append(dependency_node)
                dependency_node.children.append(node)
            else:
                if (dependency_name in self._orphaned_node_map):
                    self._orphaned_node_map[dependency_name].append(node)
                else:
                    self._orphaned_node_map[dependency_name] = [node]

        ## Add it to the list of root nodes
        if (len(node.parents) == 0 and len(dependencies) == 0):
            self.roots.append(node)

        return node


    def set_graph_loaded_state(self, state: bool):
        for node in self._node_map.values():
            node.loaded = state
