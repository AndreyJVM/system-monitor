PACKAGE_NAME = system-monitor
VERSION = $(shell cat VERSION)
DEB_FILE = ../$(PACKAGE_NAME)_$(VERSION)_all.deb

.PHONY: all clean build install remove purge reinstall version-bump

all: build

# Проверка версии
version:
	@echo "Current version: $(VERSION)"

# Увеличение версии (patch - исправления, minor - новые функции, major - критические изменения)
version-patch:
	$(eval NEW_VERSION=$(shell echo $(VERSION) | awk -F. '{print $$1"."$$2"."$$3+1}'))
	@echo $(NEW_VERSION) > VERSION
	@echo "Version bumped to $(NEW_VERSION)"
	@echo "Don't forget to update debian/changelog"

version-minor:
	$(eval NEW_VERSION=$(shell echo $(VERSION) | awk -F. '{print $$1"."$$2+1".0"}'))
	@echo $(NEW_VERSION) > VERSION
	@echo "Version bumped to $(NEW_VERSION)"
	@echo "Don't forget to update debian/changelog"

version-major:
	$(eval NEW_VERSION=$(shell echo $(VERSION) | awk -F. '{print $$1+1".0.0"}'))
	@echo $(NEW_VERSION) > VERSION
	@echo "Version bumped to $(NEW_VERSION)"
	@echo "Don't forget to update debian/changelog"

# Сборка пакета
build:
	@echo "Building $(PACKAGE_NAME) version $(VERSION)"
	@# Обновляем версию в changelog если нужно
	@if ! grep -q "$(PACKAGE_NAME) ($(VERSION))" debian/changelog; then \
		echo "WARNING: Version $(VERSION) not found in debian/changelog"; \
		echo "Run: make update-changelog"; \
	fi
	dpkg-buildpackage -us -uc -b

# Обновление changelog
update-changelog:
	@echo "Updating debian/changelog with version $(VERSION)"
	@echo "$(PACKAGE_NAME) ($(VERSION)) unstable; urgency=medium" > debian/changelog.new
	@echo "" >> debian/changelog.new
	@echo "  * New release" >> debian/changelog.new
	@echo "" >> debian/changelog.new
	@echo " -- $$(git config user.name) <$$(git config user.email)>  $$(date -R)" >> debian/changelog.new
	@echo "" >> debian/changelog.new
	@cat debian/changelog >> debian/changelog.new 2>/dev/null || true
	@mv debian/changelog.new debian/changelog

# Очистка
clean:
	@echo "Cleaning build files..."
	rm -rf ../$(PACKAGE_NAME)_$(VERSION)_*.deb
	rm -rf ../$(PACKAGE_NAME)_$(VERSION)_*.buildinfo
	rm -rf ../$(PACKAGE_NAME)_$(VERSION)_*.changes
	rm -rf debian/files
	rm -rf debian/.debhelper
	rm -rf debian/$(PACKAGE_NAME)
	rm -rf debian/*.log
	@echo "Clean complete"

# Полная очистка (включая старые версии)
clean-all:
	@echo "Cleaning all build files..."
	rm -rf ../$(PACKAGE_NAME)_*.deb
	rm -rf ../$(PACKAGE_NAME)_*.buildinfo
	rm -rf ../$(PACKAGE_NAME)_*.changes
	rm -rf debian/files
	rm -rf debian/.debhelper
	rm -rf debian/$(PACKAGE_NAME)
	rm -rf debian/*.log
	@echo "Clean complete"

# Установка
install: build
	@echo "Installing $(PACKAGE_NAME) version $(VERSION)"
	@echo "Removing old version if exists..."
	-sudo dpkg --purge $(PACKAGE_NAME) 2>/dev/null || true
	@echo "Installing new version..."
	sudo dpkg -i $(DEB_FILE)
	@echo "Fixing dependencies if needed..."
	sudo apt-get install -f -y
	@echo "Installation complete"

# Быстрая переустановка (без очистки)
reinstall:
	@echo "Reinstalling $(PACKAGE_NAME)"
	sudo dpkg --purge $(PACKAGE_NAME) 2>/dev/null || true
	sudo dpkg -i $(DEB_FILE)
	sudo apt-get install -f -y

# Удаление
remove:
	@echo "Removing $(PACKAGE_NAME)"
	sudo dpkg --purge $(PACKAGE_NAME)

# Проверка пакета
check:
	@echo "Checking package..."
	lintian $(DEB_FILE) || true

# Показать информацию о пакете
info:
	@echo "Package: $(PACKAGE_NAME)"
	@echo "Version: $(VERSION)"
	@echo "File: $(DEB_FILE)"
	@if [ -f "$(DEB_FILE)" ]; then \
		echo "Package exists: Yes"; \
		dpkg --info $(DEB_FILE); \
	else \
		echo "Package exists: No (run 'make build' first)"; \
	fi

# GitHub Release
release: build
	@echo "Creating GitHub release v$(VERSION)..."
	@# Создаем release notes
	@sed "s/{VERSION}/$(VERSION)/g" release-notes-template.md | \
	 sed "s/{REPO_OWNER}/$$(git config --get remote.origin.url | sed -n 's/.*[:/]\([^/]*\)\/\([^.]*\).*/\1/p')/g" | \
	 sed "s/{REPO_NAME}/$$(git config --get remote.origin.url | sed -n 's/.*[:/]\([^/]*\)\/\([^.]*\).*/\2/p')/g" > release-notes.md
	@# Добавляем запись из changelog
	@echo "" >> release-notes.md
	@echo "## 📝 Changelog" >> release-notes.md
	@echo "\`\`\`" >> release-notes.md
	@head -20 debian/changelog >> release-notes.md
	@echo "\`\`\`" >> release-notes.md
	@chmod +x create-release.sh
	@./create-release.sh

# Проверка готовности к релизу
release-check:
	@echo "Checking release readiness..."
	@# Проверяем что нет незакоммиченных изменений
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "$(RED)Error: Uncommitted changes exist$(NC)"; \
		git status --short; \
		exit 1; \
	fi
	@# Проверяем что версия в VERSION совпадает с git tag
	@if git tag | grep -q "v$(VERSION)"; then \
		echo "$(YELLOW)Warning: Tag v$(VERSION) already exists$(NC)"; \
	fi
	@echo "$(GREEN)Ready for release$(NC)"

# Показать команды для ручного релиза
release-help:
	@echo "To create a GitHub release:"
	@echo "  1. Update version: make version-patch (or version-minor)"
	@echo "  2. Update changelog: make update-changelog"
	@echo "  3. Build package: make build"
	@echo "  4. Create release: make release"
	@echo ""
	@echo "Or use: make release-patch (automates all steps)"

# Автоматический релиз с увеличением patch версии
release-patch: version-patch update-changelog build release

# Автоматический релиз с увеличением minor версии
release-minor: version-minor update-changelog build release

# Автоматический релиз с увеличением major версии
release-major: version-major update-changelog build release

# Показать установленные файлы
files:
	@dpkg -L $(PACKAGE_NAME) 2>/dev/null || echo "Package not installed"

# Запуск приложения
run:
	@echo "Running $(PACKAGE_NAME)..."
	system-monitor

# Полный цикл разработки
dev: clean build install run

# Цикл с увеличением версии (для исправлений)
dev-patch: version-patch update-changelog clean build install run

# Цикл с увеличением версии (для новых функций)
dev-minor: version-minor update-changelog clean build install run

# Помощь
help:
	@echo "Available commands:"
	@echo "  make version         - Show current version"
	@echo "  make version-patch   - Increment patch version (0.1.0 -> 0.1.1)"
	@echo "  make version-minor   - Increment minor version (0.1.0 -> 0.2.0)"
	@echo "  make version-major   - Increment major version (0.1.0 -> 1.0.0)"
	@echo "  make update-changelog- Update changelog with current version"
	@echo "  make build           - Build DEB package"
	@echo "  make install         - Remove old and install new package"
	@echo "  make reinstall       - Reinstall current package"
	@echo "  make remove          - Remove package"
	@echo "  make clean           - Clean build files"
	@echo "  make clean-all       - Clean all build files"
	@echo "  make check           - Check package with lintian"
	@echo "  make info            - Show package info"
	@echo "  make files           - Show installed files"
	@echo "  make run             - Run the application"
	@echo "  make dev             - Clean, build, install, run"
	@echo "  make dev-patch       - Bump patch version, build, install, run"
	@echo "  make dev-minor       - Bump minor version, build, install, run"