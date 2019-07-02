#!/bin/sh

### BEGIN INIT INFO
# Provides:          networking-sriov
# Required-Start:    mountkernfs $local_fs
# Required-Stop:     $local_fs
# Default-Start:     S
# Default-Stop:      0 6
# Short-Description: Configure SRIOV Virtual Functions
### END INIT INFO

# Authors: Frode Nordahl <frode.nordahl@gmail.com>

DESC="Configure SRIOV Virtual Functions"

. /lib/lsb/init-functions

# Include defaults if available
if [ -f /etc/default/neutron-openvswitch-networking-sriov ] ; then
    . /etc/default/neutron-openvswitch-networking-sriov
fi

if [ -z "${ENABLE}" ]; then
    ENABLE=0
fi

if [ -z "${VFS_BLANKET}" ]; then
    VFS_BLANKET=auto
fi

# Exit if feature is not enabled
[ $ENABLE -gt 0 ] || exit 0

do_start() {
    /usr/local/bin/neutron_openvswitch_networking_sriov.py --start --vfs "${VFS_LIST}" --vfs-blanket "${VFS_BLANKET}"
}

do_restart() {
    /usr/local/bin/neutron_openvswitch_networking_sriov.py --restart --vfs "${VFS_LIST}" --vfs-blanket "${VFS_BLANKET}"
}

do_stop() {
    /usr/local/bin/neutron_openvswitch_networking_sriov.py --stop --vfs "${VFS_LIST}" --vfs-blanket "${VFS_BLANKET}"
}


case "$1" in
  start)
      log_daemon_msg "$DESC"
      do_start
      ;;
  stop)
      log_daemon_msg "Un-$DESC"
      do_stop
      ;;
  systemd-start)
      do_start
      ;;
  systemd-stop)
      do_stop
      ;;
  restart)
      log_daemon_msg "Re-$DESC"
      do_stop
      do_start
      ;;
  *)
      N=/usr/local/bin/neutron-openvswitch-networking-sriov.sh
      echo "Usage: $N {start|stop|restart|systemd-start|systemd-stop}" >&2
      ;;
esac

exit 0
