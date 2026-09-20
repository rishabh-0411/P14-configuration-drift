terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.32"
    }
  }
}

provider "kubernetes" {
  config_path = pathexpand("~/.kube/config")
}

resource "kubernetes_namespace_v1" "p14" {
  metadata {
    name = "p14-demo"
  }
}

resource "kubernetes_deployment_v1" "web" {
  metadata {
    name      = "web"
    namespace = kubernetes_namespace_v1.p14.metadata[0].name

    labels = {
      app = "web"
    }
  }

  spec {
    replicas = 3

    selector {
      match_labels = {
        app = "web"
      }
    }

    template {
      metadata {
        labels = {
          app = "web"
        }
      }

      spec {
        container {
          name  = "web"
          image = "nginx:1.25"

          port {
            container_port = 80
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "128Mi"
            }

            limits = {
              cpu    = "250m"
              memory = "256Mi"
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "web" {
  metadata {
    name      = "web"
    namespace = kubernetes_namespace_v1.p14.metadata[0].name
  }

  spec {
    selector = {
      app = "web"
    }

    port {
      port        = 80
      target_port = 80
    }

    type = "ClusterIP"
  }
}

resource "kubernetes_config_map_v1" "web_config" {
  metadata {
    name      = "web-config"
    namespace = kubernetes_namespace_v1.p14.metadata[0].name

    labels = {
      owner = "team-cloud"
    }
  }

  data = {
    environment = "production"
  }
}

resource "kubernetes_service_account_v1" "web" {
  metadata {
    name      = "web"
    namespace = kubernetes_namespace_v1.p14.metadata[0].name
  }
}

resource "kubernetes_role_v1" "web" {
  metadata {
    name      = "web-role"
    namespace = kubernetes_namespace_v1.p14.metadata[0].name
  }

  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list"]
  }
}

resource "kubernetes_role_binding_v1" "web" {
  metadata {
    name      = "web-binding"
    namespace = kubernetes_namespace_v1.p14.metadata[0].name
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.web.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account_v1.web.metadata[0].name
    namespace = kubernetes_namespace_v1.p14.metadata[0].name
  }
}