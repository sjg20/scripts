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
    if func and func not in data:
        return
    to_add = '#include <%s>' % insert_hdr
    if to_add in data:
        return
    lines = data.splitlines()
    out = []
    done = False
    found_includes = False
    for line in lines:
        #if line.strip() and not done:
        if not done:
            if line.startswith('#include'):
                m = re.match('#include <(.*)>', line)
                if m:
                    hdr = m.group(1)
                    if hdr != 'common.h':
                        has_subdir = '/' in hdr
                        insert_has_subdir = '/' in insert_hdr
                        todo = False
                        if has_subdir == insert_has_subdir:
                            todo = insert_hdr < hdr
                        elif has_subdir:
                            todo = True
                        if todo:
                            out.append(to_add)
                            done = True
                found_includes = True
            elif line.startswith('#if') or line.startswith('#end'):
                 pass
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

def process_files_from(list_fname, insert_hdr):
    with open(list_fname) as fd:
        for fname in fd.readlines():
            fname = fname.strip()
            print(fname, insert_hdr)
            process_file(fname, None, insert_hdr)


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
	#doit(item + '(', 'cpu_legacy.h')

#all = 'icache_status,icache_enable,icache_disable,dcache_status,dcache_enable,'
#all += 'dcache_disable,mmu_disable'
#for item in all.split(','):
	#doit(item + '(', 'cpu_legacy.h')

#all = 'cpu_numcores,cpu_num_dspcores,cpu_mask,cpu_dsp_mask,is_core_valid,'
#for item in all.split(','):
	#doit(item + '(', 'cpu_legacy.h')

#all = 'enable_caches,flush_cache,flush_dcache_all,flush_dcache_range'
#all += ',invalidate_dcache_range,invalidate_dcache_all,invalidate_icache_all'
#all += ',cleanup_before_linux_select'
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

#all = 'eeprom_init,eeprom_read,eeprom_write'
#for item in all.split(','):
	#doit(item + '(', 'eeprom_legacy.h')

#all = 'coloured_LED_init,red_led_on,red_led_off,green_led_on,green_led_off,'
#all += 'yellow_led_on,yellow_led_off,blue_led_on,blue_led_off'
#for item in all.split(','):
	#doit(item + '(', 'status_led.h')

#all = 'flash_perror'
#for item in all.split(','):
	#doit(item + '(', 'flash.h')

#all = 'do_fat_fsload,do_ext2load'
#for item in all.split(','):
	#doit(item + '(', 'fs.h')

#all = 'relocate_code'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'jumptable_init'
#for item in all.split(','):
	#doit(item + '(', 'exports.h')

#all = 'reset_phy'
#for item in all.split(','):
	#doit(item + '(', 'net.h')

#all = 'arch_fixup_fdt'
#for item in all.split(','):
	#doit(item + '(', 'fdt_support.h')

#all = 'll_boot_init'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'get_clocks,get_bus_freq,get_serial_clock'
#for item in all.split(','):
	#doit(item + '(', 'clock_legacy.h')

#all = 'get_tbclk'
#for item in all.split(','):
	#doit(item + '(', 'time.h')

#all = 'image_load_addr,image_save_addr,image_save_size'
#for item in all.split(','):
	#doit(item, 'image.h')

#all = 'get_ram_size,get_effective_memsize'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'testdram'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'hang'
#for item in all.split(','):
	#doit(item + '(', 'hang.h')

#all = 'uuid_str_valid,uuid_str_to_bin,uuid_bin_to_str,uuid_guid_get_bin,'
#all += 'uuid_guid_get_str,gen_rand_uuid,gen_rand_uuid_str'
#for item in all.split(','):
	#doit(item + '(', 'uuid.h')

#all = 'flash_init,flash_print_info,flash_erase,flash_sect_erase,'
#all += 'flash_sect_protect,flash_sect_roundb,long flash_sector_size,'
#all += 'flash_set_verbose,flash_protect,flash_write,addr2info,write_buff,'
#all += 'cfi_mtd_init,flash_real_protect,flash_read_user_serial,'
#all += 'flash_read_factory_serial,board_flash_get_legacy,jedec_flash_match'
#for item in all.split(','):
	#doit(item + '(', 'flash.h')

#all = 'add_ip_checksums,arp_is_waiting,compute_ip_checksum,copy_filename,do_tftpb,env_get_ip,env_get_vlan,eth_env_get_enetaddr_by_index,eth_env_set_enetaddr_by_index,eth_get_dev,eth_get_dev,eth_get_dev_by_index,eth_get_dev_by_name,eth_get_dev_by_name,eth_get_dev_index,eth_get_ethaddr,eth_get_ethaddr,eth_get_name,eth_halt,eth_halt_state_only,eth_halt_state_only,eth_init,eth_init_state_only,eth_init_state_only,eth_initialize,eth_is_active,eth_is_active,eth_is_on_demand_init,eth_mcast_join,eth_parse_enetaddr,eth_receive,eth_register,eth_rx,eth_send,eth_set_current,eth_set_last_protocol,eth_try_another,eth_unregister,eth_write_hwaddr,ip_checksum_ok,ip_to_string,is_broadcast_ethaddr,is_cdp_packet,is_multicast_ethaddr,is_serverip_in_cmd,is_valid_ethaddr,is_zero_ethaddr,nc_input_packet,nc_start,net_auto_load,net_copy_ip,net_copy_u32,net_eth_hdr_size,net_get_arp_handler,net_get_async_tx_pkt_buf,net_get_udp_handler,net_init,net_loop,net_parse_bootfile,net_process_received_packet,net_random_ethaddr,net_read_ip,net_read_u32,net_send_ip_packet,net_send_packet,net_send_udp_packet,net_set_arp_handler,net_set_ether,net_set_icmp_handler,net_set_ip_header,net_set_state,net_set_timeout_handler,net_set_udp_handler,net_set_udp_header,net_start_again,net_update_ether,net_write_ip,random_port,reset_phy,string_to_ip,string_to_vlan,update_tftp,usb_eth_initialize,usb_ether_init,vlan_to_string'
#for item in all.split(','):
	#doit(item + '(', 'net.h')

#all = 'blk_get_dev,blk_get_dev,blk_get_device_by_str,blk_get_device_by_str,blk_get_device_part_str,blk_get_device_part_str,dev_print,dev_print,get_disk_guid,gpt_fill_header,gpt_fill_pte,gpt_restore,gpt_verify_headers,gpt_verify_partitions,host_get_dev_err,is_valid_dos_buf,is_valid_gpt_buf,mg_disk_get_dev,mg_disk_get_dev,part_get_info,part_get_info,part_get_info_by_dev_and_name_or_num,part_get_info_by_name,part_get_info_by_name_type,part_get_info_whole_disk,part_get_info_whole_disk,part_init,part_init,part_print,part_print,part_set_generic_name,write_gpt_table,write_mbr_and_gpt_partitions,write_mbr_partition'
#for item in all.split(','):
	#doit(item + '(', 'part.h')

#all= 'bootstage_accum,bootstage_accum,bootstage_add_record,bootstage_add_record,bootstage_error,bootstage_error,bootstage_fdt_add_report,bootstage_get_size,bootstage_get_size,bootstage_init,bootstage_init,bootstage_mark,bootstage_mark,bootstage_mark_code,bootstage_mark_code,bootstage_mark_name,bootstage_mark_name,bootstage_relocate,bootstage_relocate,bootstage_report,bootstage_start,bootstage_start,bootstage_stash,bootstage_stash,bootstage_unstash,bootstage_unstash,show_boot_progress,timer_get_boot_us'
#for item in all.split(','):
	#doit(item + '(', 'bootstage.h')

#all = 'android_image_check_header,android_image_get_end,android_image_get_kcomp,android_image_get_kernel,android_image_get_kload,android_image_get_ramdisk,android_image_get_second,android_print_contents,board_fit_config_name_match,board_fit_image_post_process,boot_fdt_add_mem_rsv_regions,boot_get_cmdline,boot_get_fdt,boot_get_fdt_fit,boot_get_fpga,boot_get_kbd,boot_get_loadable,boot_get_ramdisk,boot_get_setup,boot_get_setup_fit,boot_ramdisk_high,boot_relocate_fdt,booti_setup,bootz_setup,calculate_hash,env_get_bootm_low,env_get_bootm_mapsize,env_get_bootm_size,fdt_getprop_u32,fit_add_verification_data,fit_all_image_verify,fit_check_format,fit_check_ramdisk,fit_conf_find_compat,fit_conf_get_node,fit_conf_get_prop_node,fit_conf_get_prop_node_count,fit_conf_get_prop_node_index,fit_config_verify,fit_find_config_node,fit_get_desc,fit_get_end,fit_get_name,fit_get_node_from_config,fit_get_size,fit_get_subimage_count,fit_get_timestamp,fit_image_check_arch,fit_image_check_comp,fit_image_check_os,fit_image_check_sig,fit_image_check_target_arch,fit_image_check_type,fit_image_get_arch,fit_image_get_comp,fit_image_get_data,fit_image_get_data_and_size,fit_image_get_data_offset,fit_image_get_data_position,fit_image_get_data_size,fit_image_get_entry,fit_image_get_load,fit_image_get_node,fit_image_get_os,fit_image_get_type,fit_image_hash_get_algo,fit_image_hash_get_value,fit_image_load,fit_image_print,fit_image_verify,fit_image_verify_required_sigs,fit_image_verify_with_data,fit_parse_conf,fit_parse_subimage,fit_print_contents,fit_region_make_list,fit_set_timestamp,genimg_get_arch_id,genimg_get_arch_name,genimg_get_arch_short_name,genimg_get_cat_count,genimg_get_cat_desc,genimg_get_cat_name,genimg_get_cat_short_name,genimg_get_comp_id,genimg_get_comp_name,genimg_get_comp_short_name,genimg_get_format,genimg_get_kernel_addr,genimg_get_kernel_addr_fit,genimg_get_os_id,genimg_get_os_name,genimg_get_os_short_name,genimg_get_type_id,genimg_get_type_name,genimg_get_type_short_name,genimg_has_config,genimg_print_size,genimg_print_time,get_table_entry_id,get_table_entry_name,image_check_arch,image_check_dcrc,image_check_hcrc,image_check_magic,image_check_os,image_check_target_arch,image_check_type,image_decomp,image_get_checksum_algo,image_get_crypto_algo,image_get_data,image_get_data_size,image_get_header_size,image_get_host_blob,image_get_image_end,image_get_image_size,image_get_name,image_get_padding_algo,image_multi_count,image_multi_getimg,image_print_contents,image_set_host_blob,image_set_name,image_setup_libfdt,image_setup_linux,image_source_script,memmove_wd'
#for item in all.split(','):
	#doit(item + '(', 'bootstage.h')

#all = 'arch_cpu_init,arch_cpu_init_dm,arch_early_init_r,arch_fsp_init,arch_reserve_stacks,arch_setup_gd,board_early_init_f,board_early_init_r,board_fix_fdt,board_get_usable_ram_top,board_init_f,board_init_f_alloc_reserve,board_init_f_init_reserve,board_init_r,board_late_init,board_postclk_init,checkboard,cpu_init_r,dram_init,dram_init_banksize,embedded_dtb_select,get_effective_memsize,get_ram_size,init_cache_f_r,init_func_vid,last_stage_init,mac_read_from_eeprom,mach_cpu_init,main_loop,misc_init_f,misc_init_r,pci_init,pci_init_board,print_cpuinfo,relocate_code,relocate_code,reserve_mmu,set_cpu_clk_info,show_board_info,testdram,timer_init,trap_init,update_flash_size'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'log'
#for item in all.split(','):
	#doit(item + '(', 'log.h')

#ctags -x --c-types=fp include/log.h |cut -d' ' -f1 >asc
#ctags -x --c-types=d include/log.h |cut -d' ' -f1 >>asc
#(for f in `cat asc`; do cscope -d  -L3 $f; done) |cut -d' ' -f1 |sort |uniq

#process_files_from('files', 'log.h')

#all = 'show_regs,valid_user_regs,instruction_pointer,pc_pointer,processor_mode,'
#all += 'interrupts_enabled'

#for item in all.split(','):
	#doit(item + '(', 'asm/ptrace.h')

#all = 'BUG,BUG_ON,WARN,WARN_ON,WARN_ON_ONCE,WARN_ONCE'
#for item in all.split(','):
	#doit(item + '(', 'linux/bug.h')

#all = '__stringify'
#for item in all.split(','):
	#doit(item + '(', 'linux/stringify.h')

#all = 'udelay,__udelay,mdelay,ndelay'
#for item in all.split(','):
	#doit(item + '(', 'linux/delay.h')

#all = 'BIT,BITS_PER_BYTE,BITS_TO_LONGS,BIT_MASK,BIT_ULL,BIT_ULL_MASK,BIT_ULL_WORD,BIT_WORD,GENMASK,GENMASK,GENMASK_ULL,_LINUX_BITOPS_H,__clear_bit,__set_bit,ffs,fls'
#for item in all.split(','):
	#doit(item + '(', 'linux/bitops.h')

all = 'ft_cpu_setup,ft_pci_setup,arch_fixup_fdt'
for item in all.split(','):
	doit(item + '(', 'fdt_support.h')
