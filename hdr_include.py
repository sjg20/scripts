# Insert a header #include into all files that have a particular function call
# in them

from __future__ import print_function

import os
import re
import sys

sys.path.append('/home/sjg/u/tools/patman')

import command


def process_file(fname, func, insert_hdr):
    if fname[-2:] not in ('.c'):
        return
    with open(fname, 'r') as fd:
        data = fd.read()
    if func not in data:
        return
    to_add = '#include <%s>' % insert_hdr
    if to_add in data:
        return
    lines = data.splitlines()
    out = []
    done = False
    found_includes = False
    for line in lines:
        if not done:
            if line.startswith('#include'):
                m = re.match('#include <(.*)>', line)
                if m:
                    hdr = m.group(1)
                    if hdr != 'common.h':
                        if insert_hdr < hdr or '/' in hdr:
                            out.append(to_add)
                            done = True
                found_includes = True
            elif found_includes:
                out.append(to_add)
                done = True
        out.append(line)
    with open(fname, 'w') as fd:
        for line in out:
            print(line, file=fd)


def doit(func, insert_hdr):
    fnames = command.Output('git', 'grep', '-l', func).splitlines()
    for fname in fnames:
        if os.path.islink(fname):
            continue
        process_file(fname, func, insert_hdr)

#all = 'ENV_VALID,ENV_INVALID,ENV_REDUND'.split(',')
#all = 'env_op_create,env_op_delete,env_op_overwrite'.split(',')
#for item in all:
	#doit(item, 'search.h')

#all = 'U_BOOT_ENV_CALLBACK'.split(',')
#for item in all:
	#doit(item, 'env_callback.h')

#all = 'ENV_INVALID,ENV_INVALID,ENV_REDUND'.split(',')
#for item in all:
	#doit(item, 'env.h')

#all = 'CONFIG_ENV_SIZE,CONFIG_ENV_SECT_SIZE,ENV_OFFSET,CONFIG_ENV_ADDR'.split(',')
#all += 'ENV_IS_EMBEDDED,CONFIG_SYS_REDUNDAND_ENVIRONMENT,CONFIG_ENV_OFFSET'.split(',')
#all += 'CONFIG_SYS_REDUNDAND_ENVIRONMENT,ENV_HEADER_SIZE'.split(',')
#for item in all:
	#doit(item, 'environment.h')

#all = 'H_NOCLEAR,H_FORCE,H_INTERACTIVE,H_HIDE_DOT,H_MATCH_KEY,H_MATCH_DATA'
#all += ',H_MATCH_BOTH,H_MATCH_IDENT,H_MATCH_SUBSTR,H_MATCH_REGEX,H_MATCH_METHOD'
#all += ',H_PROGRAMMATIC,H_ORIGIN_FLAGS'
#for item in all.split(','):
	#doit(item, 'environment.h')

#all = 'ENVL_,ENV_CALLBACK_LIST_STATIC'
#for item in all.split(','):
	#doit(item, 'environment.h')


#all = 'crc32,crc32_wd,crc32_no_comp'
#for item in all.split(','):
	#doit(item + '(', 'u-boot/crc.h.h')

#all = 'qsort,strcmp_compar'
#for item in all.split(','):
	#doit(item + '(', 'sort.h')

#all = 'strmhz'
#for item in all.split(','):
	#doit(item + '(', 'vsprintf.h')

#all = 'serial_printf'
#for item in all.split(','):
	#doit(item + '(', 'serial.h')

#all = 'serial_init,serial_setbrg,serial_putc,serial_putc_raw,serial_puts'
#all += ',serial_getc,serial_tstc'
#for item in all.split(','):
	#doit(item + '(', 'serial.h')

#all = 'usec2ticks,ticks2usec'
#for item in all.split(','):
	#doit(item + '(', 'time.h')

#all = 'wait_ticks'
#for item in all.split(','):
	#doit(item + '(', 'time.h')

#all = 'timer_get_us,get_ticks'
#for item in all.split(','):
	#doit(item + '(', 'time.h')

#all = 'mii_init'
#for item in all.split(','):
	#doit(item + '(', 'linux/mii.h')

#all = 'checkcpu'
#for item in all.split(','):
	#doit(item + '(', 'cpu.h')

#all = 'smp_set_core_boot_addr,smp_kick_all_cpus'
#for item in all.split(','):
	#doit(item + '(', 'cpu.h')

#all = 'icache_status,icache_enable,icache_disable,dcache_status,dcache_enable,'
#all += 'dcache_disable,mmu_disable'
#for item in all.split(','):
	#doit(item + '(', 'cpu.h')

#all = 'cpu_numcores,cpu_num_dspcores,cpu_mask,cpu_dsp_mask,is_core_valid,'
#for item in all.split(','):
	#doit(item + '(', 'cpu_legacy.h')

#all = 'enable_caches,flush_cache,flush_dcache_all,flush_dcache_range'
#all += ',invalidate_dcache_range,invalidate_dcache_all,invalidate_icache_all'
#for item in all.split(','):
	#doit(item + '(', 'cpu_legacy.h')

#all = 'interrupt_init,timer_interrupt,external_interrupt,irq_install_handler'
#all += ',irq_free_handler,reset_timer'
#for item in all.split(','):
	#doit(item + '(', 'irq_legacy.h')

#all = 'enable_interrupts,disable_interrupts'
#for item in all.split(','):
	#doit(item + '(', 'irq_legacy.h')

#all = 'run_command,run_command_repeatable,run_command_list'
#for item in all.split(','):
	#doit(item + '(', 'command.h')

#all = 'interrupt_handler_t'
#for item in all.split(','):
	#doit(item, 'irq_legacy.h')

#all = 'board_get_usable_ram_top'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'board_fix_fdt,board_late_init,board_postclk_init,board_early_init_r'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'pci_init_board'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'trap_init'
#for item in all.split(','):
	#doit(item + '(', 'irq_legacy.h')

all = 'eeprom_init,eeprom_read,eeprom_write'
for item in all.split(','):
	doit(item + '(', 'eeprom_legacy.h')
