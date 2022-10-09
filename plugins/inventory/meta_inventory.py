from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import copy
import os

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.module_utils.six import string_types
from ansible.module_utils._text import to_native, to_text
from ansible.module_utils.common._collections_compat import MutableMapping
from ansible.plugins.inventory import BaseFileInventoryPlugin

NoneType = type(None)


class MetaInventory(object):
    meta_inventory = {}
    top_level = {}
    all_groups = {}
    debug = False

    def __init__(self, meta_inventory):
        self.meta_inventory = meta_inventory
        self.parse_meta_inventory()

    def get(self):
        """Return ansible inventory in YAML format"""

        inventory = {
            'all': {
                'children': {}
            }
        }

        for group in self.top_level:
            inventory['all']['children'][group] = self.top_level[group]

        return inventory

    def parse_meta_inventory(self):
        """Parse a meta inventory file and generate group hierarchy"""

        # Add top-level region groups
        for region_name in self.meta_inventory['regions']:
            region = {
                'name': region_name
            }
            self.add_group(region, recurse=False)

        # Collect all the top level groups
        for group in self.meta_inventory['groups']:
            self.add_group(group, recurse=False)

            # Add region groups too
            for region in self.meta_inventory['regions']:
                self.add_group(group, recurse=False, region=region)

        # Recursively descend into the meta inventory to collect all subgroups
        for group in self.meta_inventory['groups']:
            self.add_group(group, recurse=True)

            # Add region groups too
            for region in self.meta_inventory['regions']:
                self.add_group(group, recurse=True, region=region)

        # Add hosts
        for host in self.meta_inventory['hosts']:
            host_definition = {
                'name': host['name'],
                'options': {}
            }

            if 'ansible' in host:
                for ansible_opt, ansible_val in host['ansible'].items():
                    host_definition['options']['ansible_%s' % ansible_opt] = ansible_val

            # Add host to a region group
            for group_name in host['groups']:
                host_copy = copy.deepcopy(host_definition)
                self.add_host(host['region'], group_name, host_copy)

    def find_group(self, group_name):
        """Find a reference to the group object for `group_name`, if it doesn't exist create it"""

        if group_name not in self.all_groups:
            self.all_groups[group_name] = {}
        if 'children' not in self.all_groups[group_name]:
            self.all_groups[group_name]['children'] = {}

        return self.all_groups[group_name]

    def add_group(self, group, region=None, recurse=True):
        """Add a top-level group, optionally recursively creating nested groups"""

        if region:
            group_name = "%s_%s" % (region, group['name'])
            self.top_level[region]['children'][group_name] = self.find_group(group_name)

            if recurse:
                # Also add this region-specific group to the top-level group
                self.add_child(group['name'], group_name)
        else:
            group_name = group['name']
            self.top_level[group_name] = self.find_group(group_name)

        self.log("[add_group] adding %s recurse=%s" % (group_name, recurse))

        if recurse and 'groups' in group:
            for parent_group_name in group['groups']:
                self.add_child(parent_group_name, group['name'], region=region)

        if recurse and 'children' in group:
            for child in group['children']:
                self.add_subgroup(group_name, child, region=region)

    def add_subgroup(self, group_name, subgroup, region=None):
        """Add a group inside another group"""

        if region:
            subgroup_name = "%s_%s" % (region, subgroup['name'])

            # Also add this region-specific group to the regular group
            self.add_child(subgroup['name'], subgroup_name)
        else:
            subgroup_name = subgroup['name']

        self.log("[add_subgroup] adding %s to %s" % (subgroup_name, group_name))

        if group_name not in self.all_groups:
            raise AnsibleParserError("Couldn't find group %s" % group_name)
        if subgroup_name in self.all_groups:
            raise AnsibleParserError("Group name %s clashes with another group" % group_name)

        self.all_groups[group_name]['children'][subgroup_name] = self.find_group(subgroup_name)

        if 'children' in subgroup:
            for child in subgroup['children']:
                self.add_subgroup(subgroup_name, child, region=region)
        if 'groups' in subgroup:
            for parent_group_name in subgroup['groups']:
                self.add_child(parent_group_name, subgroup['name'], region=region)

    def add_child(self, group_name, child_name, region=None):
        """Add a child group to another group"""

        if region:
            child_name = "%s_%s" % (region, child_name)
            group_name = "%s_%s" % (region, group_name)

        self.log("[add_child] adding %s to %s" % (child_name, group_name))

        if group_name not in self.all_groups:
            raise AnsibleParserError("Couldn't find group %s" % group_name)

        if region:
            self.all_groups[region]['children'][group_name]['children'][child_name] = {}
        else:
            self.all_groups[group_name]['children'][child_name] = {}

    def add_host(self, region, group_name, host):
        """Add a host to a group"""

        host_name = host['name']
        region_group_name = "%s_%s" % (region, group_name)

        self.log("[add_host] adding %s to region %s group %s" % (
            host_name, region, region_group_name)
                )

        if region not in self.all_groups:
            raise AnsibleParserError("Couldn't find region %s" % region)
        if region_group_name not in self.all_groups:
            raise AnsibleParserError(
                "Couldn't find group %s in region %s" % (region_group_name, region)
                )

        if 'hosts' not in self.all_groups[region_group_name]:
            self.all_groups[region_group_name]['hosts'] = {}

        self.all_groups[region_group_name]['hosts'][host_name] = host['options']

    def log(self, mesg):
        if self.debug:
            print(mesg)


class InventoryModule(BaseFileInventoryPlugin):

    NAME = 'meta_inventory'

    def __init__(self):

        super(InventoryModule, self).__init__()

    def verify_file(self, path):

        valid = False
        if super(InventoryModule, self).verify_file(path):
            file_name, ext = os.path.splitext(path)
            if ext and ext in ['.yaml', '.yml'] and 'meta' in file_name:
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):
        ''' parses the inventory file '''

        super(InventoryModule, self).parse(inventory, loader, path)
        self.set_options()

        try:
            yaml_stream = self.loader.load_from_file(path, cache=False)
            meta_inventory = MetaInventory(yaml_stream)
            data = meta_inventory.get()
        except Exception as e:
            print("Exception generated in meta_inventory: %s" % e)
            raise AnsibleParserError(e)

        if not data:
            raise AnsibleParserError('Parsed empty YAML file')
        elif not isinstance(data, MutableMapping):
            raise AnsibleParserError('YAML inventory has invalid structure, it should be a dictionary, got: %s' % type(data))
        elif data.get('plugin'):
            raise AnsibleParserError('Plugin configuration YAML file, not YAML inventory')

        # We expect top level keys to correspond to groups, iterate over them
        # to get host, vars and subgroups (which we iterate over recursivelly)
        if isinstance(data, MutableMapping):
            for group_name in data:
                self._parse_group(group_name, data[group_name])
        else:
            raise AnsibleParserError("Invalid data from file, expected dictionary and got:\n\n%s" % to_native(data))

    def _parse_group(self, group, group_data):

        if isinstance(group_data, (MutableMapping, NoneType)):

            try:
                group = self.inventory.add_group(group)
            except AnsibleError as e:
                raise AnsibleParserError("Unable to add group %s: %s" % (group, to_text(e)))

            if group_data is not None:
                # make sure they are dicts
                for section in ['vars', 'children', 'hosts']:
                    if section in group_data:
                        # convert strings to dicts as these are allowed
                        if isinstance(group_data[section], string_types):
                            group_data[section] = {group_data[section]: None}

                        if not isinstance(group_data[section], (MutableMapping, NoneType)):
                            raise AnsibleParserError('Invalid "%s" entry for "%s" group, requires a dictionary, found "%s" instead.' %
                                                     (section, group, type(group_data[section])))

                for key in group_data:

                    if not isinstance(group_data[key], (MutableMapping, NoneType)):
                        self.display.warning('Skipping key (%s) in group (%s) as it is not a mapping, it is a %s' % (key, group, type(group_data[key])))
                        continue

                    if isinstance(group_data[key], NoneType):
                        self.display.vvv('Skipping empty key (%s) in group (%s)' % (key, group))
                    elif key == 'vars':
                        for var in group_data[key]:
                            self.inventory.set_variable(group, var, group_data[key][var])
                    elif key == 'children':
                        for subgroup in group_data[key]:
                            subgroup = self._parse_group(subgroup, group_data[key][subgroup])
                            self.inventory.add_child(group, subgroup)

                    elif key == 'hosts':
                        for host_pattern in group_data[key]:
                            hosts, port = self._parse_host(host_pattern)
                            self._populate_host_vars(hosts, group_data[key][host_pattern] or {}, group, port)
                    else:
                        self.display.warning('Skipping unexpected key (%s) in group (%s), only "vars", "children" and "hosts" are valid' % (key, group))

        else:
            self.display.warning("Skipping '%s' as this is not a valid group definition" % group)

        return group

    def _parse_host(self, host_pattern):
        '''
        Each host key can be a pattern, try to process it and add variables as needed
        '''
        (hostnames, port) = self._expand_hostpattern(host_pattern)

        return hostnames, port
