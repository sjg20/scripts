#/bin/sh

while true; do
	echo start
	qemu-system-x86_64 -bios /tmp/b/qemu-x86_64/u-boot.rom -nographic >/tmp/asc&
	pid=$!
	sleep 2
	grep "U-Boot SPL" /tmp/asc
	kill $pid
	if grep -s oprom /tmp/asc; then
		echo "bad"
		exit
	fi
	sleep 5
done
