from django.urls import include, path
from rest_framework import routers

from . import api_views as views

## URLs for app API endpoints that live under /api/v<version>/<app>/

router = routers.DefaultRouter()
router.register(r"rentalunit", views.RentalUnitViewSet)
router.register(r"contract", views.ContractViewSet)
router.register(r"resident-contract-history", views.ResidentContractHistoryViewSet, basename="resident-contract-history")
router.register(r"resident-maintenance", views.ResidentMaintenanceRequestViewSet, basename="resident-maintenance")
router.register(r"resident-invoice", views.ResidentInvoiceViewSet, basename="resident-invoice")
router.register(r"resident-invoice-history", views.ResidentInvoiceHistoryViewSet, basename="resident-invoice-history")
router.register(r"resident-contract-document", views.ResidentContractDocumentViewSet, basename="resident-contract-document")
router.register(r"resident-contract-document-history", views.ResidentContractDocumentHistoryViewSet, basename="resident-contract-document-history")

urlpatterns = [
    ## API endpoints
    path("", include(router.urls)),
    path("qrbill/", views.QRBill.as_view()),
    path("akonto/", views.Akonto.as_view()),
    path("capabilities/", views.CapabilitiesView.as_view()),
    path("resident-overview/", views.ResidentOverviewView.as_view(), name="resident-overview"),
    path("resident-portfolio/", views.ResidentPortfolioView.as_view(), name="resident-portfolio"),
    path("resident-timeline/", views.ResidentTimelineView.as_view(), name="resident-timeline"),
    path("resident-capabilities/", views.ResidentCapabilitiesView.as_view(), name="resident-capabilities"),
    path("resident-portfolio/sections/<slug:section>/", views.ResidentPortfolioSectionView.as_view(), name="resident-portfolio-section"),
]
