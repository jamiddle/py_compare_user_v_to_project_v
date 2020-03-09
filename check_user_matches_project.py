"""must restart terminal before running this file to account for changes in project-requirements.txt"""

import re
import subprocess
import click
from tabulate import tabulate
from termcolor import colored


class Checker:
    elements = []
    versions = []
    user_versions = []
    paths = []
    table = []
    project_kubectl_client_versions = {}
    project_kubectl_server_versions = {}
    user_kubectl_client_versions = {}
    user_kubectl_server_versions = {}

    @classmethod
    def handle_kubectl(cls, line):
        client_versions = []
        server_versions = []
        element, kubectl_versions = line.split('=')
        each_version = kubectl_versions.split(', ')
        for version in each_version:
            """version example: CLIENT_GIT:1.17.1"""
            if 'CLIENT' in version:
                client_versions.append(version)
            elif 'SERVER' in version:
                server_versions.append(version)
            else:
                click.echo('Version not recognised. Did you misspell "CLIENT" or "VERSION" in '
                           'project-requirements? ')
        for string in client_versions:
            """string example: CLIENT_GIT:1.17.1"""
            client_software, client_software_version = string.split(':')
            client_software_name = client_software.split('_')[1]
            """client_software_name example: GIT"""
            """client_software_version example: 1.17.1"""
            cls.project_kubectl_client_versions[
                client_software_name.capitalize()] = client_software_version

        for string in server_versions:
            """string example: SERVER_GIT:1.17.1"""
            server_software, server_software_version = string.split(':')
            server_software_name = server_software.split('_')[1]
            """server_software_name example: GIT"""
            """server_software_version example: 1.17.1"""
            cls.project_kubectl_server_versions[
                server_software_name.capitalize()] = server_software_version

        click.echo('Checking KUBECTL exists on your device...')

        try:
            path = subprocess.check_output("which kubectl", shell=True).decode("utf-8")
            click.echo('KUBECTL exists on this device')
        except subprocess.CalledProcessError:
            click.echo('it seems you do not have kubectl installed on your device')
            cls.user_versions.append('kubectl not installed')
            cls.paths.append('kubectl not installed')
            click.echo('---------------------------------------------')
            return False

        click.echo('Checking KUBECTL versions...')

        try:
            output = subprocess.check_output("kubectl version", shell=True).decode("utf-8")
        except subprocess.CalledProcessError as e:
            output = e.output.decode("utf-8")

        try:
            client_output, server_output = output.split('Server')
        except ValueError:
            client_output, server_output = output, None

        """get only the version of each software from long string in the form GitVersion:"v1.17.1"
        or GoVersion:"go1.12.11b4" """
        def find_version(output_type):
            return re.finditer('[A-Z](\w)+?[V][e][r][s][i][o][n][:]["]\S+["]', output_type)

        cls.user_kubectl_client_versions_string = find_version(client_output)
        try:
            cls.user_kubectl_server_versions_string = find_version(server_output)
        except TypeError:
            cls.user_kubectl_server_versions_string = []

        """stripper method turns string returned from calling 'kubectl version' into same format as entered
        in project-requirements.txt"""

        def stripper(i):
            a = i.group(0).strip()
            b = a.replace("Version", "")
            c, d = b.split(':')
            e = re.sub('["]', '', d).strip()
            f = re.sub('^[a-z]+', '', e).strip()
            return c, f

        """add 'name: version' to user dictionary for both client and project levels"""

        for i in cls.user_kubectl_client_versions_string:
            cls.user_kubectl_client_versions[stripper(i)[0]] = stripper(i)[1]

        for i in cls.user_kubectl_server_versions_string:
            cls.user_kubectl_server_versions[stripper(i)[0]] = stripper(i)[1]

        for project_client_key in cls.project_kubectl_client_versions:
            if project_client_key in cls.user_kubectl_client_versions:
                cls.elements.append(f"KUBECTL {project_client_key.upper()} (CLIENT)")
                cls.user_versions.append(cls.user_kubectl_client_versions[project_client_key])
                cls.versions.append(cls.project_kubectl_client_versions[project_client_key])
                cls.paths.append(path)

        for project_server_key in cls.project_kubectl_server_versions:
            if project_server_key in cls.user_kubectl_server_versions:
                cls.elements.append(f"KUBECTL {project_server_key.upper()} (SERVER)")
                cls.user_versions.append(cls.project_kubectl_client_versions[project_server_key])
                cls.versions.append(cls.project_kubectl_client_versions[project_server_key])
                cls.paths.append(path)
            else:
                cls.elements.append(f"KUBECTL {project_server_key.upper()} (SERVER)")
                cls.user_versions.append(colored("Kubectl SERVER not configured", 'red'))
                cls.versions.append(cls.project_kubectl_client_versions[project_server_key])
                cls.paths.append(path)

    @classmethod
    def check_user_version(cls, line):
        element, version = line.split('=')
        element = element.strip()
        cls.elements.append(element)
        version = version.strip()
        cls.versions.append(version)
        click.echo(f'Checking {element} exists on your device...')

        """check whether the software exists on the users path"""

        try:
            path = subprocess.check_output(f"which {element}", shell=True).decode("utf-8")
            cls.paths.append(path)
        except subprocess.CalledProcessError:
            click.echo(f'it seems you do not have {element} installed on your device')
            cls.user_versions.append(f'{element} not installed')
            cls.paths.append(f'{element} not installed')
            click.echo('---------------------------------------------')
            return False

        """check version of software on users device"""

        try:
            output = subprocess.check_output(f"{element} version", shell=True).decode("utf-8")

            """if 'version' command does not exist for this software, an error will be raised, which is handled
            by reassigning the command 'version' to '--version'. All programs seem to use either version or
            --version command"""

        except subprocess.CalledProcessError:
            output = subprocess.check_output(f"{element} --version", shell=True).decode("utf-8")
        """capture user version using regex"""
        user_version = re.search('\d(\.\d)+', output).group(0).strip()
        cls.user_versions.append(user_version)

        click.echo(f'{element} exists on this device')
        click.echo(f"Checking {element} version...")
        click.echo(user_version)
        if user_version == version:
            click.echo(f'You have the correct version ({version}) installed')
        else:
            click.echo(
                f'Incorrect version installed:\nYour version: {user_version}\nRequired version: {version}')
        click.echo('---------------------------------------------')

    @classmethod
    def print_table(cls):
        headers = ["Software", "Required Version", "Current Version", "Location"]
        for i in range(len(cls.elements)):
            if cls.versions[i - 1] == cls.user_versions[i - 1]:
                cls.table.append(
                    [colored(cls.elements[i - 1], 'green'), cls.versions[i - 1], cls.user_versions[i - 1],
                     cls.paths[i - 1]])
            else:
                cls.table.append(
                    [colored(cls.elements[i - 1], 'red'), cls.versions[i - 1], cls.user_versions[i - 1],
                     cls.paths[i - 1]])
        click.echo(tabulate(cls.table, headers, tablefmt="fancy_grid", showindex="always"))

    @classmethod
    def read_project_requirements(cls):

        """open text file containing programs and their versions required for the project. This text file must be
        written by project creator with exact name of program in uppercase, followed by equals, followed by version
        number only(no 'v') e.g. PACKER=1.5.4

        Only exception is for kubectl where syntax is as follows: KUBECTL=CLIENT_GIT:1.17.1, CLIENT_GO:1.13.6,
        SERVER_GIT:1.13.12-gke.25, SERVER_GO:1.12.11b4 'kubectl version' command returns multiple versions for both
        client and server. Prepend each version with CLIENT or SERVER, then the _SOFTWARE, then colon (:),
        then version number (entire string given by kubectl version command). """

        with open(r"project-requirements.txt") as requirements:
            for line in requirements:
                if 'KUBECTL' in line:
                    cls.handle_kubectl(line)
                else:
                    cls.check_user_version(line)

        return cls.print_table()


if __name__ == '__main__':
    Checker.read_project_requirements()
