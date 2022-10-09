### WAND Ansible Playbooks

This repo contains the set of ansible playbooks and roles for managing
machines managed by the WAND Group, at the University of Waikato.

### Playbook structure

The structure of this repo is based on the
[Ansible Best Practices](https://docs.ansible.com/ansible/playbooks_best_practices.html)
documentation, they explain how each file is used and how inventory and roles work.

### Running playbooks

You will first need to run `boot.sh` to fetch the python packages and ansible roles these playbooks use.
This also installs a python virtual environment
and the output of the script includes some options for using it.

```bash
./boot.sh
```

Note: You should re-run this boot script regularly (say once a month) to fetch
new versions of the roles.

Run this command to deploy all the base machine roles:

```bash
./venv ansible-playbook site.yml
```

You can also provide the -l option to ansible-playbook to filter which machines
are deployed.

### Using ansible vault

Generating PGP key for gpg-vault:

```bash
gpg --full-gen-key
gpg --armor --export USER@wand.net.nz
```

Re-encrypting the gpg-vault:

```bash
gpg --armor --recipient USER1@wand.net.nz --recipient USER2@wand.net.nz --encrypt --output gpg/vault-password.gpg
```

Encrypting a string for inlining into a YAML file:

```bash
./venv ansible-vault encrypt_string --stdin-name 'VARIABLE_NAME'
```

Decrypting a string from a YAML file:

```bash
cat VARS_FILE.yml | yq '.VARIABLE_NAME' | ./venv ansible-vault decrypt
```

### Inventory group assignment

In order to be flexible with how machines are configured, we make use of a large
number of nested groups to ensure the correct variables are set for each machine
depending on role or region.

To manage the nested groups, we use a custom dynamic inventory plugin called
meta inventory to full-mesh all the appropriate groups together.

Debugging the group memberships by looking at the inventory definition alone
can be challenging. It is recommended to use ansible-inventory to inspect which
variables are attached to a host:

```bash
./venv ansible-inventory --yaml --host [hostname]
```

An entire inventory can be dumped as well:

```bash
./venv ansible-inventory -i inventories/production --yaml --list
```

Or to show the group hierarchy you can use:


```bash
./venv ansible-inventory -i inventories/production --graph [group]
```

The format for the meta inventory file is as follows, this file needs the word
`meta` somewhere in the filename and a .yaml or .yml file extension.

The groups section allows us to define our hierarchy of nested groups. This is
a list of top level groups and then subgroups can be defined as `children` of
a top level group. Any group or subgroup can be a member of a list of other
`groups`.


```yaml
groups:
  - name: servers
    description: server machines
    children:
      - name: trace_servers
        description: servers for dealing with network packets
        groups:
          - ldap
          - nfs_home
```

A region is simply a name, this will be prepended on all the groups you have
configured in the groups section, (e.g bluecables\_servers and
bluecables\_trace\_servers). You can use the debug commands above to work out
all new groups that were created.

```yaml
hosts:
  bluecables: {}
```

A host definition must always have a region and a list of roles, we can also
optionally define ansible\_ vars such as (ansible\_host):

```yaml
hosts:
  - name: foobar.wand.nz
    region: bluecables
    groups:
      - desktops
    ansible:
      host: 10.0.0.1
      user: ansible
```

### Provisioning machines

```bash
./venv ansible-playbook -l [hostname | group] provision.yml
```

*Note: Only run this the first time a machine is deployed,
then `site.yml` for subsequent Ansible runs.*

*Note: Ansible will prompt you for a BECOME password,
this is your sudo password rather than that of the provision user*

This playbook is used to provision all types of machines. This includes:

* Machines created via installation media
* OpenNebula virtual machines
* Raspberry Pi devices

If you want to configure credentials for the initial user installed on a machine,
then you can set these variables as group_vars or host_vars:

```yaml
# Defaults:
provision_user_username: "ansible"
provision_user_password: ""  # Use empty string to be prompted
```

Or use the --extra-vars argument for ansible-playbook:

```bash
./venv ansible-playbook --extra-vars "provision_user_username=ansible" -l [hostname | group] provision.yml
```

If password-based SSH authentication is necessary, set `provision_ssh_password_authentication` to `true` in group_vars or host_vars:

```yaml
provision_ssh_password_authentication: true
```

Or use --extra-vars:

```bash
./venv ansible-playbook --extra-vars "provision_ssh_password_authentication=true" -l [hostname | group] provision.yml
```

The provision playbook will initially connect to the machine as the provision user,
so you will be prompted for a passphrase for the provision key:

```
Enter passphrase for key 'ssh/ansible_ed25519':
```

This can be retrieved by running:

```bash
./venv ansible-vault view ssh/ansible_ed25519_password
```

When the provision playbook gets to stage 2,
it will connect to the machine using your user credentials.
To avoid interruptions during the provision playbook,
make sure your ssh key is loaded into an ssh-agent before running the playbook.

**Provisioning virtual machines**

Make sure `one_frontend`, `one_api_username`, `one_api_password` are set.
For each host you also need to set `one_vm` (see example below).

Required vars (with examples):

```yaml
one_frontend: "opennebula.front.end"

one_api_username: "ansible"
one_api_password: "secret"

one_vm:
  host: "vm.host"              # Specific host to deploy VM on (optional, required for block storage)
  host_type: "production"      # Host type to deploy the VM on (optional)
  memory: "4GB"                # VM memory (required)
  cpu: 2                       # VM cpus (required)
  os: "Debian 10"              # Must match image name in OpenNebula (required)
  size: "100GB"                # Root disk size (required)
  block_storage:               # Attach logical volumes to VM (optional)
    - datastore: "DS Name"     # Must match datastore name in OpenNebula (required)
      size: "1000GB"           # Logical volume size (required)
  extra_storage:               # Extra VM disks (optional)
    - config:                  # Use OpenNebula VM template variables from the disk section (required)
        type: "swap"
        dev_prefix: "vd"
      size: "4GB"              # Disk size (required)
  nics:                        # NICs to attach to the VM (required)
    - network: "bluecables"    # Must match network name in OpenNebula (required)
      ip: "10.0.0.1"           # Initial NIC ipv4 address (required)
  extra_config: ""             # String for extra OpenNebula VM template configuration (optional)
```

Add the host(s) to the `opennebula_vms` group.

Run the `provision.yml` playbook and provide a secure random password when prompted.
When the VM is created the provision user's password is set to this.

**Site playbook stages**

The site playbook is split up into stages.
This is to allow us to cleanly switch from a provision user
to your normal user during an initial deployment.

`site.stage1.yml`:
Used for running tasks that need to be run early on in the build process.
This includes configuring networking, configuring users, setting up apt sources,
updating/configuring the kernel, storage (e.g. NFS), and SSH config.
It is important that this stage ends with your normal user able to login to the machine via ssh.
Since some machines mount an NFS home, this stage will end with the provision user
losing ssh access due to their 'authorized_keys' being removed.

`site.stage2.yml`:
Mainly used for applying specific roles to machines based on their group membership.
This stage also applies base roles that are applied to all machines.
When making additions to the site playbook it's more likely this is the stage that should be updated.
