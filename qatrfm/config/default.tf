variable "num_domains" {
    default = "1"
}

variable "net_octet" {
}

variable "image" {
}

variable "basename" {
}

variable "ram" {
    default = "1024"
}

variable "cores" {
    default = "1"
}

provider "libvirt" {
     uri = "qemu:///system"
}

resource "libvirt_volume" "myvdisk" {
  name = "qatrfm-vdisk-${var.basename}-${count.index}.qcow2"
  count = "${var.num_domains}"
  pool = "default"
  source = "${var.image}"
  format = "qcow2"
}

resource "libvirt_network" "my_net" {
   name = "qatrfm-net-${var.basename}"
   addresses = ["10.${var.net_octet}.0.0/24"]
   dhcp {
        enabled = true
    }
}

resource "libvirt_domain" "domain-sle" {
  name = "qatrfm-vm-${var.basename}-${count.index}"
  memory = "${var.ram}"
  vcpu = "${var.cores}"
  count = "${var.num_domains}"

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
