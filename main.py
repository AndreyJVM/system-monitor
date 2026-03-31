#!/usr/bin/env python3
# main.py

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')  # Добавляем требование для Gdk
from gi.repository import Gtk, GLib, Gdk  # Импортируем Gdk
import psutil
import socket
import platform
import os
from datetime import datetime

class SystemMonitor(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="System Monitor")
        self.set_default_size(500, 400)
        self.set_border_width(15)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Стилизация (с обработкой ошибок)
        try:
            self.setup_styling()
        except Exception as e:
            print(f"Warning: Could not load CSS styling: {e}")
        
        # Основной контейнер
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(vbox)
        
        # Заголовок
        header = Gtk.Label()
        header.set_markup("<big><b>System Information Monitor</b></big>")
        vbox.pack_start(header, False, False, 0)
        
        # Создаем grid для информации
        grid = Gtk.Grid()
        grid.set_column_spacing(15)
        grid.set_row_spacing(10)
        vbox.pack_start(grid, True, True, 0)
        
        # Создаем метки
        row = 0
        self.labels = {}
        info_items = [
            ("🌐 IP Address:", "ip"),
            ("📡 DNS Servers:", "dns"),
            ("💿 Operating System:", "os"),
            ("💾 Disks:", "disk"),
            ("🧠 RAM:", "ram"),
            ("🕐 Last Update:", "time")
        ]
        
        for label_text, key in info_items:
            # Название
            title = Gtk.Label()
            title.set_markup(f"<b>{label_text}</b>")
            title.set_xalign(0)
            grid.attach(title, 0, row, 1, 1)
            
            # Значение
            value = Gtk.Label()
            value.set_xalign(0)
            value.set_line_wrap(True)
            value.set_max_width_chars(50)
            grid.attach(value, 1, row, 1, 1)
            
            self.labels[key] = value
            row += 1
        
        # Добавляем кнопку обновления
        button_box = Gtk.Box(spacing=10)
        refresh_btn = Gtk.Button(label="🔄 Refresh Now")
        refresh_btn.connect("clicked", self.on_refresh_clicked)
        button_box.pack_end(refresh_btn, False, False, 0)
        vbox.pack_start(button_box, False, False, 0)
        
        # Первое обновление
        self.update_data()
        
        # Таймер обновления (каждые 10 секунд)
        GLib.timeout_add_seconds(10, self.update_data)
    
    def setup_styling(self):
        """Добавляем CSS стили"""
        css = b"""
        window {
            background-color: #f5f5f5;
        }
        label {
            font-family: Monospace;
            font-size: 11px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
        }
        button:hover {
            background-color: #45a049;
        }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        
        # Получаем экран и применяем стили
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
    
    def get_ip_address(self):
        """Получение IP адреса"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "❌ Unable to determine"
    
    def get_dns_servers(self):
        """Получение DNS серверов"""
        try:
            with open('/etc/resolv.conf', 'r') as f:
                dns = []
                for line in f:
                    if line.startswith('nameserver') and not line.startswith('#'):
                        dns.append(line.split()[1])
            if dns:
                return ', '.join(dns[:3])
            else:
                return "⚠️ No DNS servers found"
        except:
            return "❌ Unable to read DNS configuration"
    
    def get_os_info(self):
        """Детальная информация об ОС"""
        try:
            # Определяем дистрибутив
            distro = ""
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            distro = line.split('=')[1].strip('"')
                            break
            
            if not distro:
                distro = f"{platform.system()} {platform.release()}"
            
            kernel = platform.version().split('-')[0] if '-' in platform.version() else platform.version()
            # Ограничиваем длину строки
            if len(kernel) > 50:
                kernel = kernel[:47] + "..."
            return f"{distro}\n(Kernel: {kernel})"
        except:
            return f"{platform.system()} {platform.release()}"
    
    def get_disk_info(self):
        """Информация о дисках с прогресс-барами"""
        disk_parts = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                # Создаем текстовый прогресс-бар
                percent = usage.percent
                bars = int(percent / 10)
                bar = '█' * bars + '░' * (10 - bars)
                used_gb = usage.used // (1024**3)
                total_gb = usage.total // (1024**3)
                disk_parts.append(
                    f"{partition.mountpoint}: {bar} {percent:.0f}% "
                    f"({used_gb}/{total_gb}GB)"
                )
            except (PermissionError, OSError):
                # Пропускаем разделы, к которым нет доступа
                continue
            except Exception:
                continue
        
        if disk_parts:
            # Ограничиваем количество строк
            if len(disk_parts) > 5:
                disk_parts = disk_parts[:5] + ["..."]
            return '\n'.join(disk_parts)
        return "⚠️ No disk information available"
    
    def get_ram_info(self):
        """Информация о RAM с прогресс-баром"""
        ram = psutil.virtual_memory()
        percent = ram.percent
        bars = int(percent / 10)
        bar = '█' * bars + '░' * (10 - bars)
        used_gb = ram.used // (1024**3)
        total_gb = ram.total // (1024**3)
        return f"{bar} {percent:.0f}% ({used_gb}/{total_gb} GB)"
    
    def update_data(self):
        """Обновление всей информации"""
        try:
            self.labels['ip'].set_text(self.get_ip_address())
            self.labels['dns'].set_text(self.get_dns_servers())
            self.labels['os'].set_text(self.get_os_info())
            self.labels['disk'].set_text(self.get_disk_info())
            self.labels['ram'].set_text(self.get_ram_info())
            self.labels['time'].set_text(datetime.now().strftime("%H:%M:%S"))
        except Exception as e:
            print(f"Error updating data: {e}")
            # Показываем ошибку в интерфейсе
            self.labels['ip'].set_text(f"Error: {str(e)[:50]}")
        
        return True  # Продолжаем таймер
    
    def on_refresh_clicked(self, button):
        """Обработчик кнопки обновления"""
        self.update_data()
        # Визуальная обратная связь
        original_label = button.get_label()
        button.set_label("✓ Updated!")
        # Возвращаем исходный текст через 1 секунду
        GLib.timeout_add_seconds(1, lambda: button.set_label(original_label))

def main():
    app = SystemMonitor()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()