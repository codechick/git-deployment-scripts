#!/usr/bin/python
# MIT License
# 2015 www.codeChick.it Buk! Buk!

import os
import re
import subprocess
import shutil
import distutils.dir_util
import errno
import sys

class Deployment:
    'It automatizes the deployment from a bare repository to the deployment space.'
    __colors =    {
                    'OK'      : '\033[92m',
                    'ERR'     : '\033[91m',
                    'clear'   : '\033[0m'
                }
    deployments_dir = os.path.abspath(os.path.join(os.sep, 'var', 'deployments'))
    branch = 'deploy_test'
    srv_docs_path = os.path.abspath(os.path.join(os.sep, 'var','www','test'))
    print_prefix = 'TMB> '

    def __print(self, message, color_name='OK', prefix=None):
        'Helper class to simply print log messages while deploying'
        color = self.__colors.get(color_name, '\033[92m')

        if prefix is None:
            prefix = self.print_prefix

        print str(color + prefix + message), str(self.__colors['clear'])

    def __stash_modules_changes(self, op='save'):
        exit_code = 0

        if op not in ('save', 'pop'):
            raise ValueError("Bad argument: %s" % op)

        try:
            if op == 'save':
                self.__print('Stashing all the modules...')
                cmd = self.__cmd_prefix + "submodule foreach 'git stash save -u';"
                exit_code = subprocess.call(cmd, stderr=subprocess.STDOUT, shell=True)
            else:
                self.__print('Reapplying stash to the modules...')
                cmd = self.__cmd_prefix + "submodule foreach 'git stash pop ||:'"
                exit_code = subprocess.call(cmd, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            self.__print('An error occoured and stashing has terminated unexpectedly.', 'ERR')
            ret = e.output
            exit_code = 1

        if exit_code == 0:
            self.__print('Done')
        else:
            self.__print('Stashing met some errors. Proceding anyway', 'ERR')

#        self.__output_history.append({'op': 'stash_modules_changes', 'out': ret})

        if exit_code == 0:
            return True
        else:
            return False

    def __stash_it(self):
        exit_code = 0
        self.__print('Stashing the website...')

        cmd = self.__cmd_prefix + "stash save --all"
        exit_code = subprocess.call(cmd, stderr=subprocess.STDOUT, shell=True)

        if exit_code == 0:
            self.__print('Done')
            return True
        else:
            self.__print('Stashing met some errors. Proceding anyway', 'ERR')
            return False

    def __create_deployment_structure(self):
        #git bare repositories do not have the stash folder by default. I'll create it in order to save the work tree
        self.__print('Creating missing structures...')

        dir_to_create = os.path.join(self.git_dir, 'logs', 'refs')

        try:
            if not os.path.exists(dir_to_create):
                os.makedirs(dir_to_create)

            stash_file_path = os.path.join(dir_to_create, 'stash')
            if not os.path.exists(stash_file_path):
                f = open(stash_file_path, 'w')
                f.close()

            if not os.path.exists(self.bck_dir):
                os.makedirs(self.bck_dir)

            if not os.path.exists(self.git_work_tree):
                os.makedirs(self.git_work_tree)
        except:
            self.__print('Some errors have occoured while initializing the missing structure.', 'ERR')
            return False

        return True


    def __backup_actual_site(self):
        self.__print('Creating the new backup')

        #removing last backup to replace it
        try:
           for the_file in os.listdir(self.bck_dir):
                file_path = os.path.join(self.bck_dir, the_file)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        except:
            self.__print('Some errors have occoured while creating the new backup', 'ERR')
            return False

        #copying backup
        distutils.dir_util.copy_tree(self.git_work_tree, self.bck_dir, preserve_symlinks=True)

        self.__print('Backup created.')
        self.__print('Pointing srv to backup...')


        try:
            os.symlink(self.bck_dir, self.srv_site_path)
        except OSError as e:
            if e.errno == errno.EEXIST:
                os.remove(self.srv_site_path)
                os.symlink(self.bck_dir, self.srv_site_path)
            else:
                self.__print('An unexpected error occoured while linking the new backup', 'ERR')
                return False

        self.__print('Done.')
        return True


    def __checkout_new_version(self):
        exit_code = 0
        self.__print('Checking out the new version...')

        #we are talking about bare repositories. Hence we have to specify where the HEAD points
        cmd = "git symbolic-ref HEAD refs/heads/%s;" % self.branch
        cmd += self.__cmd_prefix + 'checkout -f;'
        cmd += self.__cmd_prefix + 'submodule init;'
        cmd += self.__cmd_prefix + 'submodule sync;'
        cmd += self.__cmd_prefix + 'submodule update;'

        exit_code = subprocess.call(cmd, stderr=subprocess.STDOUT, shell=True)

        if exit_code == 0:
            self.__print('Checkout done')
            return True
        else:
            self.__print('Checkout met some errors. Proceding anyway', 'ERR')
            return False

    def __unstash_it(self):
        self.__print('Unstashing...')
        cmd = self.__cmd_prefix + 'stash show'
        exit_code = subprocess.call(cmd, stderr=subprocess.STDOUT, shell=True)

        if exit_code > 0:
            self.__print('No stashing to apply. Skipping...')
            return True

        cmd = self.__cmd_prefix + 'stash pop'
        exit_code = subprocess.call(cmd, stderr=subprocess.STDOUT, shell=True)

        if exit_code == 0:
            self.__print('Unstashed.')
            return True
        else:
            self.__print('Stashing met some errors. Proceding anyway', 'ERR')
            return False

    def __unlink_shared_folders(self):
        self.__print('Linking shared directories...')

        #scanning the share directory. the direcoty to symlink in the share will replicate the subfolder tree and a symlink will be added
        #when a subfolder contains at least a file
        for dir_path, subdir_list, file_list in os.walk(self.shr_dir, True):
            if len(file_list) == 0:
                continue

            subdir_list[:] = []

            symlink_path = os.path.join(self.git_work_tree, os.path.relpath(dir_path, self.shr_dir))
            os.remove(symlink_path)

            symlink_path = os.path.join(self.bck_dir, os.path.relpath(dir_path, self.shr_dir))
            os.remove(symlink_path)

        self.__print('Unlinked.')
        return True


    def __link_shared_folders(self):
        self.__print('Linking shared directories...')

        #scanning the share directory. the direcoty to symlink in the share will replicate the subfolder tree and a symlink will be added
        #when a subfolder contains at least a file
        for dir_path, subdir_list, file_list in os.walk(self.shr_dir, True):
            if len(file_list) == 0:
                continue

            #files found! No need to dig further. Here is where we have to link to
            subdir_list[:] = []

            symlink_path = os.path.join(self.git_work_tree, os.path.relpath(dir_path, self.shr_dir))
            try:
                os.symlink(dir_path, symlink_path)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    os.remove(symlink_path)
                    os.symlink(dir_path, symlink_path)
                else:
                    self._print('An unexpected error occoured while creating the symlinks', 'ERR')
                    return False

            symlink_path = os.path.join(self.bck_dir, os.path.relpath(dir_path, self.shr_dir))
            try:
                os.symlink(dir_path, symlink_path)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    os.remove(symlink_path)
                    os.symlink(dir_path, symlink_path)
                else:
                    self._print('An unexpected error occoured while creating the symlinks', 'ERR')
                    return False

        self.__print('Linking Done.')
        return True


    def __print_confirmation(self):
        head = "*********************** TEMBO DEPLOY ***********************"
        self.__print(head, prefix='')
        self.__print('* ' + 'Site deployed successfully :-)'.center(len(head)-4, ' ') + ' *', prefix='')

        str = '%s pointing to the backup' % self.srv_site_path
        self.__print('* ' + str.center(len(head)-4, ' ') + ' *', prefix='')

        self.__print('* ' + 'Remember to launch kumi-tools for upgrading'.center(len(head)-4, ' ') + ' *', prefix='')

        str = 'Then change the symlink to %s' % self.git_work_tree
        self.__print('* ' + str.center(len(head)-4, ' ') + ' *', prefix='')
        self.__print('*' * len(head), prefix='')


    def __change_permissions(self, paths=None, mode=0775):
        'mode parameter is intended as an octal value (leading 0 is needed)'
        if paths is None:
            paths = [self.git_work_tree, self.bck_dir]
        elif isinstance(paths, list):
            paths = [paths]

        self.__print('Changing the permissions to %s...' % mode)

        for path in paths:
            self.__print('Changing to %s' % path)
            for root, dirs, files in os.walk(path, topdown=False):
                for dir in [os.path.join(root,d) for d in dirs]:
                    os.chmod(dir, mode)
            for file in [os.path.join(root, f) for f in files]:
                os.chmod(file, mode)

        self.__print('Permissions changed.')

        return True


    def __test_first_deploy(self):
        if os.path.exists(self.git_work_tree) and len(os.listdir(self.git_work_tree)) > 0:
            return False

        return True


    def pre_deploy(self):
        first_deploy = self.__test_first_deploy()

        if first_deploy:
            if not self.__create_deployment_structure():
                self.__print('Terminating the deployment prematurely.', 'ERR')
                sys.exit(1)
        else:
            if not self.__backup_actual_site():
                self.__print('Terminating the process prematurely.', 'ERR')
                return

            if not self.__unlink_shared_folders():
                self.__print('Terminating the deployment prematurely.', 'ERR')
                sys.exit(1)

            if not self.__stash_modules_changes():
                self.__print('Terminating the deployment prematurely.', 'ERR')
                self.__print(self.__output_history[0]['out'])
                sys.exit(1)

            if not self.__stash_it():
                self.__print('Terminating the process prematurely.', 'ERR')
                sys.exit(1)

        sys.exit()


    def deploy(self):
        first_deploy = self.__test_first_deploy()

        if not self.__checkout_new_version():
            self.__print('Terminating the process prematurely.', 'ERR')
            return

        if not first_deploy:
            if not self.__unstash_it():
                self.__print('Terminating the process prematurely.', 'ERR')
                return

            if not self.__stash_modules_changes('pop'):
                self.__print('Terminating the process prematurely.', 'ERR')
                return

        if not self.__link_shared_folders():
            self.__print('Terminating the process prematurely.', 'ERR')
            return

        if not self.__change_permissions():
            self.__print('Terminating the process prematurely.', 'ERR')
            return

        self.__print_confirmation()


    def __init__(self):
        self.__output_history = []
        self.git_dir = os.getcwd()
        self.site_name = None
        self.git_work_tree = None
        self.bck_dir = None

        match_git_dir = re.search(r'.*/(.*).git$',self.git_dir)
        if match_git_dir:
            self.site_name = match_git_dir.group(1)
            self.git_work_tree = os.path.join(self.deployments_dir, self.site_name, 'p')
            self.shr_dir = os.path.join(self.deployments_dir, self.site_name, 'shr')
            self.bck_dir = os.path.join(self.deployments_dir, self.site_name, 'b')
            self.srv_site_path = os.path.join(self.srv_docs_path, self.site_name)

            #because of a git bug, you have to execute git-submodule inside the work_treee, notwithstanding the --work-tree parameter
            self.__cmd_prefix = "cd %s; " % self.git_work_tree
            self.__cmd_prefix += "git --git-dir=%s --work-tree=%s " % (self.git_dir, self.git_work_tree)
