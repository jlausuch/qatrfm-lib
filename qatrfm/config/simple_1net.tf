variable "count" {
    default = "2"
}

variable "network" {
}

variable "image" {
}

provider "libvirt" {
     uri = "qemu:///system"
}

resource "random_id" "service" {
    count = "${var.count}"
    byte_length = 4
}

resource "libvirt_volume" "myvdisk" {
  name = "qatrfm-vdisk-${element(random_id.service.*.hex, count.index)}.qcow2"
  count = "${var.count}"
  pool = "default"
  source = "${var.image}"
  format = "qcow2"
}

resource "libvirt_network" "my_net" {
   name = "qatrfm-net-${element(random_id.service.*.hex, count.index)}"
   addresses = ["${var.network}"]
   dhcp {
		enabled = true
	}
}

resource "libvirt_domain" "domain-sle" {
  name = "qatrfm-vm-${element(random_id.service.*.hex, count.index)}"
  memory = "2048"
  vcpu = 2
  count = "${var.count}"

  network_interface {
    network_id = "${libvirt_network.my_net.id}"
    wait_for_lease = true
  }

  disk {
   volume_id = "${libvirt_volume.myvdisk.*.id[count.index]}"
  }

  console {
    type        = "pty"
    target_port = "0"
    target_type = "serial"
  }

  console {
      type        = "pty"
      target_type = "virtio"
      target_port = "1"
  }

  graphics {
    type = "vnc"
    listen_type = "address"
    autoport = "true"
  }
}

output "domain_ips" {
    value = "${libvirt_domain.domain-sle.*.network_interface.0.addresses}"
}

output "domain_names" {
    value = "${libvirt_domain.domain-sle.*.name}"
}
