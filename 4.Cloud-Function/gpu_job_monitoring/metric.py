#!/usr/bin/python

"""
Pushes nVidia GPU metrics to a Prometheus Push gateway for later collection.
"""

import argparse
import logging
import time
import platform
import math

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from prometheus_client import start_http_server, core

from pynvml import *


log = logging.getLogger('nvidia-tool')


def _create_parser():
    parser = argparse.ArgumentParser(description='nVidia GPU Prometheus '
                                                 'Metrics Exporter')
    parser.add_argument('--verbose',
                        help='Turn on verbose logging',
                        action='store_true')

    parser.add_argument('-u', '--update-period',
                        help='Period between calls to update metrics, '
                             'in seconds. Defaults to 30.',
                        default=30)

    parser.add_argument('-g', '--gateway',
                        help='If defined, gateway to push metrics to. Should '
                             'be in the form of <host>:<port>.',
                        default=None)

    parser.add_argument('-p', '--port',
                        help='If non-zero, port to run the http server',
                        type=int,
                        default=0)

    return parser


def main():
    parser = _create_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
   
    registry = core.REGISTRY

    total_fb_memory = Gauge('gpu_total_fb_memory_mb',
                            'Total installed frame buffer memory (in '
                            'megabytes)',
                            ['device'],
                            registry=registry)
    free_fb_memory = Gauge('gpu_free_fb_memory_mb',
                           'Unallocated frame buffer memory (in '
                           'megabytes)',
                           ['device'],
                           registry=registry)
    used_fb_memory = Gauge('gpu_used_fb_memory_mb',
                           'Allocated frame buffer memory (in megabytes).'
                           ' Note that the diver/GPU will always set '
                           'a small amount of memory fore bookkeeping.',
                           ['device'],
                           registry=registry)
    gpu_utilization = Gauge('gpu_utilization_pct',
                            'Percent of time over the past sample period '
                            'during which one or more kernels was '
                            'executing on the GPU.',
                            ['device'],
                            registry=registry)
    memory_utilization = Gauge('gpu_mem_utilization_pct',
                               'Percent of time over the past sample '
                               'period during which global (device) memory '
                               'was being read or written',
                               ['device'],
                               registry=registry)
							   
							   
    clock_speed = Gauge('gpu_clock_speed',
                        'Clock speed in the MHz',
                        ['device'],
                        registry=registry)
							   
							   
    power_usage = Gauge('gpu_power_usage',
                        'Power Usage of the GPU in KW',
                        ['device'],
                        registry=registry)
							   
							   
    temperature = Gauge('gpu_temperature',
                        'Temperature of the GPU in degree C',
                        ['device'],
                        registry=registry)

    iteration = 0

    try:
        log.debug('Initializing NVML...')
        nvmlInit()
        print("Initialized")

        log.info('Started with nVidia driver version = %s', 
                 nvmlSystemGetDriverVersion())

        device_count = nvmlDeviceGetCount()
        log.info('%d devices found.', device_count)

        
        log.info('Starting http server on port %d', 8080)
        start_http_server(1010)
        log.info('HTTP server started on port %d', 8080)

        while True:

            iteration += 1
            log.info('Current iteration = %d', iteration)

            for i in range(device_count):
                log.info('Analyzing device %d...', i)
                try:
                    log.info('Obtaining handle for device %d...', i)
                    handle = nvmlDeviceGetHandleByIndex(i)
                    log.info('Device handle for %d is %s', i, str(handle))

                    log.info('Querying for memory information...')
                    mem_info = nvmlDeviceGetMemoryInfo(handle)
                    log.info('Memory information = %s', str(mem_info))

                    total_fb_memory.labels(device=i).set(mem_info.total / 1024 ** 3)
                    free_fb_memory.labels(device=i).set(mem_info.free / 1024 ** 3) 
                    used_fb_memory.labels(device=i).set(mem_info.used / 1024 ** 3)

                    log.info('Obtaining utilization statistics...')
                    utilization = nvmlDeviceGetUtilizationRates(handle)
                    log.info('Utilization GPU statistics = %s', str(utilization.gpu))
                    log.info('Utilization Memory statistics = %s', str(math.trunc(mem_info.used / mem_info.total * 100)))

			
                    gpu_utilization.labels(device=i).set(utilization.gpu)
                    memory_utilization.labels(device=i).set(math.trunc(mem_info.used / mem_info.total * 100))
		    
                    #clock_info = nvmlDeviceGetClock(handle,0,0)
                    #clock_speed.labels.set(device=i).set(clock_info.real)
                    #log.info('Clock statistics = %s', str(clock_info))
		
                    #power_value = nvmlDeviceGetPowerUsage(handle)
                    #power_usage.labels.set(device=i).set(power_value.real/1000.0)
                    #log.info('Power Usage statistics = %s', str(power_value))
				
                    #temperature_value = nvmlDeviceGetTemperature(handle)
                    #temperature.labels.set(device=i).set(temperature_value)
                    #log.info('Temperature statistics = %s', str(temperature_value))
				
                except Exception as e:
                    log.info(e, exc_info=True)


                log.info('Pushing metrics to gateway at %s...', args.gateway)
                hostname = platform.node()
                print(hostname)
                print(core.REGISTRY)
                push_to_gateway(args.gateway+':9091', job=hostname, registry=core.REGISTRY)
                log.info('Push complete.')

                
            time.sleep(2)
        
    except Exception as e:
        log.info('Exception thrown - %s', e, exc_info=True)
    finally:
        nvmlShutdown()
   

if __name__ == '__main__':
    main()
