import runpy
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "usr/libexec/nobara-resolve-pkexec"
)
SCRIPT = runpy.run_path(str(SCRIPT_PATH))
has_amd_gpu = SCRIPT["has_amd_gpu"]
required_packages = SCRIPT["required_packages"]


def add_pci_device(root: Path, name: str, vendor: str, device_class: str) -> None:
    device = root / name
    device.mkdir()
    (device / "vendor").write_text(vendor, encoding="ascii")
    (device / "class").write_text(device_class, encoding="ascii")


class AmdGpuDetectionTests(unittest.TestCase):
    def test_detects_only_amd_display_controllers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            pci_devices = Path(temporary_directory)
            add_pci_device(pci_devices, "amd-audio", "0x1002", "0x040300")
            add_pci_device(pci_devices, "nvidia-gpu", "0x10de", "0x030000")

            self.assertFalse(has_amd_gpu(pci_devices))

            add_pci_device(pci_devices, "amd-gpu", "0x1002", "0x038000")
            self.assertTrue(has_amd_gpu(pci_devices))

    def test_unavailable_or_malformed_sysfs_is_not_a_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            pci_devices = Path(temporary_directory)
            add_pci_device(pci_devices, "malformed", "AMD", "display")
            self.assertFalse(has_amd_gpu(pci_devices))
            self.assertFalse(has_amd_gpu(pci_devices / "missing"))


class RequiredPackageTests(unittest.TestCase):
    def test_installs_the_zlib_compatible_runtime_by_its_real_name(self) -> None:
        for amd_gpu_present in (False, True):
            packages = required_packages(amd_gpu_present)
            self.assertIn("zlib-ng-compat", packages)
            self.assertNotIn("zlib", packages)

    def test_rocm_is_installed_only_for_amd_gpus(self) -> None:
        self.assertNotIn("rocm-meta", required_packages(False))
        self.assertIn("rocm-meta", required_packages(True))

    def test_deprecated_runtime_and_wrapper_dependency_are_removed(self) -> None:
        for amd_gpu_present in (False, True):
            packages = required_packages(amd_gpu_present)
            self.assertNotIn("nobara-resolve-runtime", packages)
            self.assertNotIn("python3.11", packages)
            self.assertNotIn("python3.11-libs", packages)

    def test_installer_package_check_is_not_bypassed(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("SKIP_PACKAGE_CHECK", source)


if __name__ == "__main__":
    unittest.main()
