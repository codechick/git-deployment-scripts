# Deployment scripts

## What it does and how
The scripts exploit the git's repositoty hooks, `post-update` and `pre-receive`, in order to be able to push new websites
and deploy them.

### Backup and production versions
Deployment exploits a rapid fallback by keeping the new deployed and a backup of the previous version of the website.

e.g.
deployment dir: `/var/deployments/kumi`
backup website (when pushing): `/var/deployments/kumi/b`

The web server will point to the backup or the new version by symlinking:
webserver dir for the website: `/var/www/kumi`

new website (when pushing): `/var/deployments/kumi/p`
backup (actual site, before pushing): `/var/deployments/kumi/b`

When pushing, the script automatically points to the backup (actual version). It's up to the *BOFH* to change the symlink

### "Shared directories" are supported
When it comes to bloating git projects with giga of images and other bloody folders, those dirs are not deployed
by means of git and they are never replicated so as to save the holy disk space. The scripts reads the `shr` content
into the deployment space and symlinks each dir/file found by replicating the dir structure found.

E.g.
shr contains the `img` dir: `/var/deployments/kumi/shr/img`.
When the website is deployed, both the _backup_ and the _production_ versions will point to that img-folder, sharing it:

    /var/deployments/kumi/b/img -> /var/deployments/kumi/shr/img
    /var/deployments/kumi/p/img -> /var/deployments/kumi/shr/img

### Modified production files are kept
Did you modify the production version under `/var/deployments/kumi/p/`? Nein, nein, nein! The script takes care of it
 by stashing both the project and the submodules and reapplying it after checking out. Be careful, though, modifying that way stinks.

## Pre-requisites
1. The server must be accessible by means of SSH for pushes
2. The server must have Python 2.7.x installed. No, no 3.
3. Git must be installed (duh)
4. The websites must have a git bare repository on the machine

## Installation
You have to manually copy these three files:

+ `deployment.py` is the core of everything. It can be placed everywhere but must be executable by the username
 that will push new contents.
+ `post-update` and `pre-receive` are the scripts that exploit `deployment.py`. You have two options to use them:
    - Copy them into `/usr/share/git-core/templates/hooks/` or into the proper folder where git-templates are located.
     They will be copied and used for each new initialized project by means of `git init --bare`. **HEADS UP**: if you don't
      wanna use them of a particular project you should remove them after initializing the repository.
    - Copy them into each repository under the proper `hooks` directory

## Configuration
### deployment.py
attributes can be modified straightforward in the class, otherwise you can simply override them at the end of the file by writing

    Deployment.<attr_name> = <preferred-val>

by modifiying `deployment.py` all the projects will have those values. You can also modify some values on a project basis 
by placing the overrides **both** in `pre-receive` and `post-updated` located in each repository hook folder. The right
place to put your overrides are marked by a comment:

    # Deployment's overrides here
    deployment.<attr_name> = <preferred-val>

The configurable values are:
+ `deployments_dir`: it is the directory where the _sharing dir_, the _production_ and the _sharing_ are kept
+ `branch`: the branch that will be checked out
+ `srv_docs_path`: the path where the symlink towards the _production_ or the _backup_ is placed (usually `/var/www`)
+ `user_name`: both *backup* and *production* deployments (b and p folders) will have this UNIX user. Useful for srv execution purposes
+ `group_name`: both *backup* and *production* deployments (b and p folders) will have this UNIX group. Useful for srv execution purposes
+ `print_prefix`: fashion mannerism. It's the prefix placed on all the script outputs

### post-update and pre-receive
+ `deployment_script_path`: the path where the deployment.py is placed so as to load and use it.

Some configurations are automatically set, but the user can override them once the deployment instance object is
 instantiated. A comment in both scripts tells you where to place these overrides:

 E.g.:
    deployment = dep.Deployment()

    # Deployment's overrides here
    deployment.site_name = 'buk'

 The overridable attributes are:
 + site_name
 + git_work_tree
 + shr_dir
 + bck_dir
 + srv_site_path

 Please read Deployment's code in case you don't understand what they stand for. It's auto-explicative.


## Copyright
2015 codeChick.it - matteo@codechick.it. MIT license