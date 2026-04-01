#!/usr/bin/env python3
# main.py - Исправленная стабильная версия

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import psutil
import socket
import platform
import os
from datetime import datetime

class SystemMonitor(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="System Monitor")
        self.set_default_size(550, 450)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Основной контейнер
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)
        
        # Заголовок
        header = Gtk.Label()
        header.set_markup("<big><b>System Information Monitor</b></big>")
        vbox.pack_start(header, False, False, 0)
        
        # Создаем scrolled window для длинного контента
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scrolled, True, True, 0)
        
        # Создаем grid для информации
        grid = Gtk.Grid()
        grid.set_column_spacing(15)
        grid.set_row_spacing(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_left(10)
        grid.set_margin_right(10)
        scrolled.add(grid)
        
        # Создаем метки
        self.labels = {}
        info_items = [
            ("IP Address:", "ip"),
            ("DNS Servers:", "dns"),
            ("Operating System:", "os"),
            ("Disk Usage:", "disk"),
            ("RAM Usage:", "ram"),
            ("Last Update:", "time")
        ]
        
        row = 0
        for label_text, key in info_items:
            # Название
            title = Gtk.Label()
            title.set_markup(f"<b>{label_text}</b>")
            title.set_xalign(0)
            title.set_halign(Gtk.Align.START)
            grid.attach(title, 0, row, 1, 1)
            
            # Значение
            value = Gtk.Label()
            value.set_xalign(0)
            value.set_halign(Gtk.Align.START)
            value.set_line_wrap(True)
            value.set_selectable(True)  # Позволяет копировать текст
            grid.attach(value, 1, row, 1, 1)
            
            self.labels[key] = value
            row += 1
        
        # Кнопка обновления
        button_box = Gtk.Box(spacing=10)
        refresh_btn = Gtk.Button(label="Refresh Now")
        refresh_btn.connect("clicked", self.on_refresh_clicked)
        button_box.pack_end(refresh_btn, False, False, 0)
        vbox.pack_start(button_box, False, False, 0)
        
        # Статус бар
        self.statusbar = Gtk.Statusbar()
        self.status_context = self.statusbar.get_context_id("status")
        vbox.pack_start(self.statusbar, False, False, 0)
        
        # Первое обновление
        self.update_data()
        
        # Таймер обновления (каждые 10 секунд)
        GLib.timeout_add_seconds(10, self.update_data)
    
    def get_ip_address(self):
        """Получение IP адреса"""
        try:
            # Пробуем получить через socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            # Альтернативный метод
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                return f"{ip} (fallback)"
            except:
                return f"Error: {str(e)[:50]}"
    
    def get_dns_servers(self):
        """Получение DNS серверов"""
        try:
            dns = []
            # Пробуем прочитать resolv.conf
            if os.path.exists('/etc/resolv.conf'):
                with open('/etc/resolv.conf', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('nameserver') and not line.startswith('#'):
                            parts = line.split()
                            if len(parts) > 1:
                                dns.append(parts[1])
            
            if dns:
                return ', '.join(dns[:3])
            else:
                # Пробуем systemd-resolved
                if os.path.exists('/run/systemd/resolve/resolv.conf'):
                    with open('/run/systemd/resolve/resolv.conf', 'r') as f:
                        for line in f:
                            if line.startswith('nameserver'):
                                dns.append(line.split()[1])
            
            return ', '.join(dns[:3]) if dns else "Using system defaults"
        except Exception as e:
            return f"Error: {str(e)[:50]}"
    
    def get_os_info(self):
        """Информация об ОС"""
        try:
            # Получаем информацию об ОС
            system = platform.system()
            release = platform.release()
            
            # Пробуем получить имя дистрибутива
            distro = ""
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            distro = line.split('=')[1].strip('"')
                            break
            
            if distro:
                return f"{distro}\nKernel: {release}"
            else:
                return f"{system} {release}\nKernel: {platform.version()[:50]}"
        except Exception as e:
            return f"Error: {str(e)[:50]}"
    
    def get_disk_info(self):
        """Информация о дисках"""
        try:
            disk_parts = []
            for partition in psutil.disk_partitions():
                # Пропускаем специальные файловые системы
                if partition.fstype in ['squashfs', 'tmpfs', 'devtmpfs']:
                    continue
                
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    percent = usage.percent
                    used_gb = usage.used // (1024**3)
                    total_gb = usage.total // (1024**3)
                    
                    # Создаем простой текстовый прогресс-бар
                    bar_length = 20
                    filled = int(bar_length * percent / 100)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    
                    disk_parts.append(
                        f"{partition.mountpoint:15} [{bar}] {percent:5.1f}%  ({used_gb:3}/{total_gb:3} GB)"
                    )
                except (PermissionError, OSError):
                    continue
                except Exception:
                    continue
            
            if disk_parts:
                # Показываем все разделы, но ограничиваем вывод
                result = '\n'.join(disk_parts[:8])
                if len(disk_parts) > 8:
                    result += f"\n... and {len(disk_parts) - 8} more"
                return result
            else:
                return "No disk information available"
        except Exception as e:
            return f"Error: {str(e)[:50]}"
    
    def get_ram_info(self):
        """Информация о RAM"""
        try:
            ram = psutil.virtual_memory()
            percent = ram.percent
            used_gb = ram.used // (1024**3)
            total_gb = ram.total // (1024**3)
            
            # Создаем прогресс-бар
            bar_length = 30
            filled = int(bar_length * percent / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            # Дополнительная информация
            available_gb = ram.available // (1024**3)
            
            return (f"[{bar}] {percent:.1f}%\n"
                   f"Used: {used_gb} GB / Total: {total_gb} GB\n"
                   f"Available: {available_gb} GB")
        except Exception as e:
            return f"Error: {str(e)[:50]}"
    
    def update_data(self):
        """Обновление всей информации"""
        try:
            # Обновляем каждую метку с обработкой ошибок
            self.labels['ip'].set_text(self.get_ip_address())
            self.labels['dns'].set_text(self.get_dns_servers())
            self.labels['os'].set_text(self.get_os_info())
            self.labels['disk'].set_text(self.get_disk_info())
            self.labels['ram'].set_text(self.get_ram_info())
            self.labels['time'].set_text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            # Обновляем статус бар
            self.statusbar.push(self.status_context, "✓ Updated successfully")
            
        except Exception as e:
            print(f"Error updating data: {e}")
            self.statusbar.push(self.status_context, f"✗ Error: {str(e)[:50]}")
        
        return True  # Продолжаем таймер
    
    def on_refresh_clicked(self, button):
        """Обработчик кнопки обновления"""
        # Меняем текст кнопки
        original_text = button.get_label()
        button.set_label("Updating...")
        button.set_sensitive(False)
        
        # Обновляем данные
        self.update_data()
        
        # Возвращаем кнопку в исходное состояние
        GLib.timeout_add_seconds(1, lambda: self.reset_button(button, original_text))
    
    def reset_button(self, button, original_text):
        """Возвращает кнопку в исходное состояние"""
        button.set_label(original_text)
        button.set_sensitive(True)
        return False

def main():
    app = SystemMonitor()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()