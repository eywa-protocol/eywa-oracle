import yaml
import requests
import subprocess
import re
from os import geteuid, system, path, mkdir, listdir, getenv


required_commands = ['systemctl',
                     'docker',
                     'apt',
                     'pacman',
                     'timedatectl',
                     '/usr/lib/systemd/systemd-timesyncd']

required_daemon = ['docker',
                   'systemd-timesyncd']

config_files = ['bridge.yaml', 'bsn.yaml', 'hmy.yaml', 'solana.yaml']

networks = ['prod', 'idiv1', 'dev2', 'your own choice']

def _exit(msg, code):
    print(f"{msg}\nexit code {code}")
    exit(code)


def restart_daemon(_daemon):
    system(f"systemctl restart {_daemon}")
    if not check_daemon(_daemon):
        system(f"systemctl stop {_daemon}")
        system(f"systemctl enable --now {_daemon}")
        if not check_daemon(_daemon):
            _exit(f"daemon '{_daemon}' start error", 1)


def run_daemon(_daemon):
    system(f"systemctl enable --now {_daemon}")
    if not check_daemon(_daemon):
        system(f"systemctl stop {_daemon}")
        system(f"systemctl enable --now {_daemon}")
        if not check_daemon(_daemon):
            _exit(f"daemon '{_daemon}' start error", 1)
    else:
        if _daemon == 'systemd-timesyncd':
            restart_daemon(_daemon)
    print(f"daemon '{_daemon}' is running")


def check_daemon(_daemon):
    status = system(f"systemctl status {_daemon} > /dev/null")
    if status == 0:
        return True
    elif status == 768:
        return False
    else:
        return False

def user_pick(question_text: str, options: list, last_is_manual: bool):
    print(question_text)

    for i, item in enumerate(options, start=1):
        print(f"{i}) {item}")

    choice = input("Enter number: ")
    try:
        if not last_is_manual and 0 < int(choice) <= len(options):
            return options[int(choice) - 1]
        elif last_is_manual and 0 < int(choice) < len(options):
            return options[int(choice) - 1]
        elif last_is_manual and int(choice) == len(options):
            return input("Input your value: ")
        else:
            return user_pick(question_text, options, last_is_manual)
    except:
        return user_pick(question_text, options, last_is_manual)

class Check:
    @classmethod
    def check_file(cls, file_path):
        if path.isfile(file_path):
            # print("Файл существует")
            return True
        else:
            # print("Файл не существует")
            return False
    @classmethod
    def check_dir(cls, dir_path):
        if path.isdir(dir_path):
            # print("Директория существует")
            return True
        else:
            # print("Директория не существует")
            return False

    @classmethod
    def root(cls):
        if geteuid() != 0:
            _exit("Please run as root", 1)
        return True

    @classmethod
    def check_time_sync(cls):
        sync_info_raw = subprocess.run('timedatectl', stdout=subprocess.PIPE)
        sync_info = sync_info_raw.stdout.decode('UTF-8').split('\n')
        sync_info = [ k.strip() for k in sync_info ]
        synced = True if sync_info[4].split(': ')[1] == 'yes' else False
        timesyncd_enabled = True if sync_info[5].split(': ')[1] == 'active' else False

        if not timesyncd_enabled and synced:
            print(f"WARNING! Time synced ok, but systemd-timesyncd is not running!")
        elif not synced:
            _exit(f"Time sync False.\n{sync_info_raw.stdout.decode('UTF-8')}", 1)
        return synced and timesyncd_enabled

    @classmethod
    def check_node_key(cls, key):
        key_pattern = r"0x[a-zA-Z0-9]{40}"
        if re.fullmatch(key_pattern, key):
            return True
        else:
            _exit(f"Node key '{key}' does not match regex '0x[a-zA-Z0-9]{40}'", 1)


class Facts:

    def __init__(self,
                 _node_name,
                 _keystore_password,
                 network_name,
                 default_ntp = "0.pool.ntp.org",
                 timesyncd_config_path = "/etc/systemd/timesyncd.conf",
                 app_dir = '/app'):
        if not _node_name:
            _exit("Node name is required", 1)
        self.ntp = default_ntp
        self.node_name = _node_name
        self.dependencies = {}
        self.missing_dependencies = []
        self.package_manager = False
        self.docker_install_command = False
        self.timesyncd_install_command = False
        self.timesyncd_config_path = timesyncd_config_path
        self.app_dir = app_dir
        self.init_config_base_url = "https://bridge-configs.eywa.fi/"
        self.network_name = network_name
        self.init_config_file = {}
        self.chains = []
        self.prometheus_port = 10300
        self.loki_addr = getenv("LOKI_ADDR", False)
        self.keystore_password = _keystore_password
        self.bridge_use_pusher = 1

    @property
    def get_bridge_yaml(self):
        bridge_yaml = {}
        with open(f"{self.app_dir}/{self.node_name}/bridge.yaml", 'r') as by:
            try:
                bridge_yaml = yaml.safe_load(by)
            except yaml.YAMLError as e:
                _exit(f"Error parce yaml '{self.app_dir}/{self.node_name}/bridge.yaml'\n"
                      f"With error:\n{e}", 1)
        return bridge_yaml

    @property
    def get_hmy_yaml(self):
        hmy_yaml = {}
        with open(f"{self.app_dir}/{self.node_name}/hmy.yaml", 'r') as hy:
            try:
                hmy_yaml = yaml.safe_load(hy)
            except yaml.YAMLError as e:
                _exit(f"Error parce yaml '{self.app_dir}/hmy.yaml'\n"
                      f"With error:\n{e}", 1)
        return hmy_yaml

    @property
    def get_chains(self):
        if not self.chains:
            for chain in self.get_bridge_yaml['chains']:
                self.chains.append(chain['id'])
        return self.chains

    @property
    def get_chains_string(self):
        return [ str(c) for c in self.get_chains ]

    @property
    def get_config_base_url(self):
        return f"{self.init_config_base_url}/{self.network_name}/"

    @property
    def get_node_name(self):
        return self.node_name

    @property
    def get_app_dir(self):
        return self.app_dir

    @property
    def app_dir_exist(self):
        return Check.check_dir(self.get_app_dir)

    @property
    def get_missing_dependencies(self):
        return self.missing_dependencies

    @property
    def init_config(self):
        return self.init_config_file

    @property
    def get_init_config(self):
        r = requests.get(f"{self.init_config_base_url}/{self.network_name}/init_config.json")
        self.init_config_file = r.json()
        return self.init_config

    @property
    def get_rendezvous(self):
        return self.init_config['rendezvous']

    @property
    def get_image(self):
        return self.init_config['bridge_image']

    @property
    def get_package_manager(self):
        return self.package_manager

    @property
    def get_dependencies(self):
        return self.dependencies

    @property
    def set_package_manager(self):
        #DEUBG
        # self.get_dependencies["pacman"] = False
        # print(self.get_dependencies)
        if self.get_dependencies["pacman"]:
            self.package_manager = 'pacman'
            self.docker_install_command = "pacman -Syy --noconfirm docker"
            self.timesyncd_install_command = "pacman -Syy --noconfirm systemd"

        elif self.get_dependencies["apt"]:
            self.package_manager = 'apt'
            self.docker_install_command = "apt update; apt install -y docker.io"
            self.timesyncd_install_command = "apt update; apt install -y systemd-timesyncd"
        else:
            self.package_manager = False
        del self.dependencies['pacman']
        del self.dependencies['apt']
        return self.get_package_manager

    @property
    def check_dependencies(self):
        for k,v in self.dependencies.items():
            if not v:
                self.missing_dependencies.append(k)
        return True, self.get_dependencies if not self.missing_dependencies else False, self.missing_dependencies

    @property
    def get_bridge_init_command(self):
        init_command = f"docker run -l bridge -t --rm " \
                       f"--name {self.node_name} " \
                       f"-h {self.node_name} " \
                       f"-p 8081:8081 " \
                       f"-p 10300:10300 " \
                       f"-p 45554:45554 " \
                       f"-e NTP_RETRY={self.ntp} " \
                       f"-e KEYSTORE_PASSWORD={self.keystore_password} " \
                       f"-v {self.app_dir}/.data/keys/:/keys " \
                       f"-v {self.app_dir}/.data/leveldb/{self.node_name}:/leveldb " \
                       f"-v {self.app_dir}/{self.node_name}:/app " \
                       f"{self.get_image} " \
                       f"./bridge -verbosity 0 -init " \
                       f"-cnf /app/bridge.yaml -sol-cnf /app/solana.yaml -hmy-cnf /app/hmy.yaml 2>&1"
        return init_command

    @property
    def get_bridge_reg_command(self):
        reg_command = f"docker run -l bridge -t --rm " \
                      f"-h {self.node_name} " \
                      f"--name {self.node_name} " \
                      f"-p 8081:8081 " \
                      f"-p 10300:10300 " \
                      f"-p 45554:45554 " \
                      f"-e NTP_RETRY={self.ntp} " \
                      f"-e KEYSTORE_PASSWORD={self.keystore_password} " \
                      f"-v {self.app_dir}/.data/keys/:/keys " \
                      f"-v {self.app_dir}/.data/leveldb/{self.node_name}:/leveldb " \
                      f"-v {self.app_dir}/{self.node_name}:/app " \
                      f"{self.get_image} " \
                      f"./bridge -verbosity 4 -register 1 " \
                      f"-cnf /app/bridge.yaml -sol-cnf /app/solana.yaml -hmy-cnf /app/hmy.yaml 2>&1 | grep ERROR"
        return reg_command

    @property
    def get_bridge_run_command(self):
        if self.loki_addr:
          run_command = f"docker run -l bridge -d " \
                        f"--name {self.node_name} " \
                        f"-h {self.node_name} " \
                        f"-p 8081:8081 " \
                        f"-p 10300:10300 " \
                        f"-p 45554:45554 " \
                        f"-e NTP_RETRY={self.ntp} " \
                        f"-e PROM_LISTEN_PORT={self.prometheus_port} " \
                        f"-e KEYSTORE_PASSWORD={self.keystore_password} " \
                        f"-e BRIDGE_USE_PUSHER={self.bridge_use_pusher} " \
                        f"-v {self.app_dir}/.data/keys/:/keys " \
                        f"-v {self.app_dir}/.data/leveldb/{self.node_name}:/leveldb " \
                        f"-v {self.app_dir}/{self.node_name}:/app " \
                        f"--log-driver=loki " \
                        f"--log-opt loki-url={self.loki_addr}/loki/api/v1/push " \
                        f"--log-opt loki-external-labels=name={self.node_name} " \
                        f"{self.get_image} " \
                        f"./bridge -verbosity 4 " \
                        f"-cnf /app/bridge.yaml -sol-cnf /app/solana.yaml -hmy-cnf /app/hmy.yaml 2>&1"
        else:
          run_command = f"docker run -l bridge -d " \
                        f"--name {self.node_name} " \
                        f"-h {self.node_name} " \
                        f"-p 8081:8081 " \
                        f"-p 10300:10300 " \
                        f"-p 45554:45554 " \
                        f"-e NTP_RETRY={self.ntp} " \
                        f"-e PROM_LISTEN_PORT={self.prometheus_port} " \
                        f"-e KEYSTORE_PASSWORD={self.keystore_password} " \
                        f"-e BRIDGE_USE_PUSHER={self.bridge_use_pusher} " \
                        f"-v {self.app_dir}/.data/keys/:/keys " \
                        f"-v {self.app_dir}/.data/leveldb/{self.node_name}:/leveldb " \
                        f"-v {self.app_dir}/{self.node_name}:/app " \
                        f"{self.get_image} " \
                        f"./bridge -verbosity 4 " \
                        f"-cnf /app/bridge.yaml -sol-cnf /app/solana.yaml -hmy-cnf /app/hmy.yaml 2>&1"
        return run_command

    def check_command(self, _command):
        if system(f"command -v {_command} > /dev/null") == 0:
            self.dependencies[_command] = True
        else:
            self.dependencies[_command] = False
        return self.get_dependencies


class Actions:
    def __init__(self, _facts):
        self.facts = _facts
        self.package_manager = _facts.set_package_manager
        self.node_key = ""

    @property
    def get_node_kye(self):
        return self.node_key

    @property
    def get_bridge_image(self):
        print(f"pull bridge image '{self.facts.get_image}'")
        if system(f"docker pull {self.facts.get_image} > /dev/null") != 0:
            _exit(f"Error pull bridge image with name '{self.facts.get_image}'", 1)
        return True

    def create_dir(self, dir_path):
        try:
            mkdir(dir_path)
            print(f"{dir_path}/{self.facts.get_node_name}")
            mkdir(f"{dir_path}/{self.facts.get_node_name}")
            mkdir(f"{dir_path}/.data")
        except Exception as e:
            _exit(f"Can't create dir '{dir_path}'", 1)

    def timesyncd_config_replace(self):
        if automatic_install:
            change = 'Y'
        else:
            change = input(f"Replace ntp server ({self.facts.timesyncd_config_path}) to '{self.facts.ntp}'? (Y/n) ") or "Y"
        while change != "Y" and change != "n":
            change = input(
                f"Replace ntp server ({self.facts.timesyncd_config_path}) to '{self.facts.ntp}'? (Y/n) ") or "Y"

        if change == "Y":
            with open(self.facts.timesyncd_config_path, 'w') as config:
                new_config = f"[Time]\nNTP={self.facts.ntp}\n"
                config.write(new_config)
        else:
            print(f"\nWARNING! The ntp server has not been changed, this may lead to errors in the future\n")

    def try_install_deps(self):
        # DEUBG
        # self.facts.missing_dependencies.append('docker')
        self.facts.check_dependencies

        if 'docker' not in self.facts.missing_dependencies and '/usr/lib/systemd/systemd-timesyncd' not in self.facts.missing_dependencies:
            if self.facts.missing_dependencies:
                 _exit(f"missing dependencies: {' ,'.join(self.facts.missing_dependencies)}", 1)
        if 'docker' in self.facts.missing_dependencies:
            self.install_docker()
        if '/usr/lib/systemd/systemd-timesyncd' in self.facts.missing_dependencies:
            self.install_timesyncd()
        return True

    def install_docker(self):
        if not self.package_manager:
            _exit(f"\nDocker not installed and package manager unsupported.\n"
                  f"Supported package manager: pacman, apt.\n"
                  f"You can install docker manually and restart this script\n", 1)

        if automatic_install:
            install = 'Y'
        else:
            install = input(f"Install docker with command: {self.facts.docker_install_command} (Y/n) ") or "Y"

        while install != "Y" and install != "n":
            install = input(f"Install docker with command: {self.facts.docker_install_command} (Y/n) ")

        if install == "Y":
            if system(self.facts.docker_install_command) != 0:
                _exit(f"Docker install failed.\nCommand:\n{self.facts.docker_install_command}\n", 1)
        else:
            _exit(f"\nDocker is not installed.\nYou can install docker manually and restart this script", 1)
        return True

    def install_timesyncd(self):
        if not self.package_manager:
            _exit(f"\Timesyncd not installed and package manager unsupported.\n"
                  f"Supported package manager: pacman, apt.\n"
                  f"You can install timesyncd manually and restart this script\n", 1)

        if automatic_install:
            install = 'Y'
        else:
            install = input(f"Install systemd-timesyncd with command: {self.facts.timesyncd_install_command} (Y/n) ") or "Y"

        while install != "Y" and install != "n":
            install = input(f"Install systemd-timesyncd with command: {self.facts.timesyncd_install_command} (Y/n) ")

        if install == "Y":
            if system(self.facts.timesyncd_install_command) != 0:
                _exit(f"Timesyncd install failed.\nCommand:\n{self.facts.timesyncd_install_command}\n", 1)
        else:
            _exit(f"\Timesyncd is not installed.\nYou can install timesyncd manually and restart this script", 1)
        return True

    def get_config_files(self, files):
        for file in files:
            r = requests.get(f"{self.facts.init_config_base_url}/{self.facts.network_name}/{file}")
            with open(f"{self.facts.get_app_dir}/{self.facts.get_node_name}/{file}", 'w') as f:
                f.write(r.text)

    def init_bridge(self):
        new_key = subprocess.run(self.facts.get_bridge_init_command, stdout=subprocess.PIPE, shell=True)
        self.node_key = new_key.stdout.decode('UTF-8').strip()
        return self.get_node_kye

    def reg_bridge(self):
        raw_result = subprocess.run(self.facts.get_bridge_reg_command, stdout=subprocess.PIPE, shell=True)
        result = raw_result.stdout.decode('UTF-8')
        if result:
            _exit(f"Node registration error with:\n\n{result}", 1)
        return True

    def run_bridge(self):
        result = system(self.facts.get_bridge_run_command)
        if result != 0:
            _exit(f"Node run error with code '{result}'", 1)
        return result



if __name__ == "__main__":
    print("""
Welcome!
supported software:
1) services: systemd
2) package manager: pacman, apt
3) ntp service: systemd-timesyncd
4) containers: docker""")

    try:
        old_node_name = [d for d in listdir('/app') if 'node' in d][0]
    except:
        old_node_name = None

    if old_node_name:
        node_name = input(f"Input your node name ({old_node_name}): ")
    else:
        node_name = input(f"Input your node name: ")

    network_name = user_pick("Input which network your node will connect to:", networks, True)

    keystore_password = input(f"Input your secret password of the keystore of this private node: ")

    automatic_install = input("Manual or fully automatic installation (A/m): ") or "A"
    automatic_install = True if automatic_install == "A" else False
    if old_node_name and not node_name:
        facts = Facts(old_node_name, keystore_password, network_name)
    else:
        facts = Facts(node_name, keystore_password, network_name)

    print("Get facts")
    Check.root()
    for command in required_commands:
        facts.check_command(command)

    action = Actions(facts)
    action.try_install_deps()

    action.timesyncd_config_replace()
    if automatic_install:
        approval = "Y"
    else:
        approval = input(f"The next services '{', '.join(required_daemon)}' will be running automatically (Y/n): ") or "Y"

    if approval == "Y":
        for daemon in required_daemon:
            run_daemon(daemon)
    else:
        stopped_daemons = []
        for daemon in required_daemon:
            if not check_daemon(daemon):
                stopped_daemons.append(daemon)
        if stopped_daemons:
            _exit(f"The next services not running, fix it and try again.\n{', '.join(stopped_daemons)}", 1)

    Check.check_time_sync()

    print("\nDependencies satisfied\n")
    print("Preparing to start the node\n")



    if not facts.app_dir_exist:
        action.create_dir(facts.get_app_dir)

    if not facts.get_init_config:
        _exit(f"Not found '{facts.get_config_base_url}/init_config.json'", 1)

    action.get_config_files(config_files)
    action.get_bridge_image
    node_key = action.init_bridge()
    if Check.check_node_key(node_key):
        input(f"You public node key:\n"
              f"------------------------------------------\n"
              f"{node_key}\n"
              f"------------------------------------------\n"
              f"Now you need to top up your balance in the following networks: fantom, testnet.\n"
              f"Token EYWA (at current time you can get token EYWA by request to tech team)\n"
              f"And press enter to continue...")

        action.reg_bridge()
        action.run_bridge()
