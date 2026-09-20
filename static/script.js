/* ==========================================================================
   AI-Powered Resume Analyzer - Client Interactive Scripts
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // ------------------------------------------------------------------
  // 1. Auto-dismiss Flash Alerts after 5 seconds
  // ------------------------------------------------------------------
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.5s ease';
      setTimeout(() => alert.remove(), 500);
    }, 5000);
  });

  // ------------------------------------------------------------------
  // 2. Custom Target Role Toggle on Upload Form
  // ------------------------------------------------------------------
  const roleSelect = document.getElementById('target_role_select');
  const customRoleGroup = document.getElementById('custom_role_group');
  const customRoleInput = document.getElementById('custom_target_role');

  if (roleSelect && customRoleGroup) {
    roleSelect.addEventListener('change', (e) => {
      if (e.target.value === 'Custom Role') {
        customRoleGroup.style.display = 'block';
        customRoleInput.setAttribute('required', 'required');
      } else {
        customRoleGroup.style.display = 'none';
        customRoleInput.removeAttribute('required');
      }
    });
  }

  // ------------------------------------------------------------------
  // 3. File Upload Drag & Drop + Size & PDF Validation
  // ------------------------------------------------------------------
  const uploadBox = document.getElementById('uploadDropzone');
  const fileInput = document.getElementById('resumeFileInput');
  const fileDetails = document.getElementById('selectedFileDetails');
  const fileNameDisplay = document.getElementById('selectedFileName');

  if (uploadBox && fileInput) {
    ['dragenter', 'dragover'].forEach(eventName => {
      uploadBox.addEventListener(eventName, (e) => {
        e.preventDefault();
        uploadBox.classList.add('dragover');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      uploadBox.addEventListener(eventName, (e) => {
        e.preventDefault();
        uploadBox.classList.remove('dragover');
      }, false);
    });

    uploadBox.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length > 0) {
        fileInput.files = files;
        validateAndShowFile(files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        validateAndShowFile(e.target.files[0]);
      }
    });
  }

  function validateAndShowFile(file) {
    const maxSizeMB = 5;
    const maxSizeBytes = maxSizeMB * 1024 * 1024;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Invalid file format. Please upload a PDF file only.');
      fileInput.value = '';
      if (fileDetails) fileDetails.style.display = 'none';
      return;
    }

    if (file.size > maxSizeBytes) {
      alert(`File size exceeds ${maxSizeMB} MB. Please select a smaller PDF.`);
      fileInput.value = '';
      if (fileDetails) fileDetails.style.display = 'none';
      return;
    }

    if (fileNameDisplay && fileDetails) {
      fileNameDisplay.textContent = `${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
      fileDetails.style.display = 'block';
    }
  }

  // ------------------------------------------------------------------
  // 4. Live Client-Side Job Filtering (Jobs Board)
  // ------------------------------------------------------------------
  const searchInput = document.getElementById('jobSearchInput');
  const skillFilterSelect = document.getElementById('skillFilterSelect');
  const jobCards = document.querySelectorAll('.job-card-item');

  if (searchInput || skillFilterSelect) {
    const filterJobs = () => {
      const query = (searchInput ? searchInput.value : '').toLowerCase().trim();
      const selectedSkill = (skillFilterSelect ? skillFilterSelect.value : '').toLowerCase().trim();

      jobCards.forEach(card => {
        const title = card.getAttribute('data-title').toLowerCase();
        const company = card.getAttribute('data-company').toLowerCase();
        const location = card.getAttribute('data-location').toLowerCase();
        const skills = card.getAttribute('data-skills').toLowerCase();

        const matchesSearch = !query || 
          title.includes(query) || 
          company.includes(query) || 
          location.includes(query) || 
          skills.includes(query);

        const matchesSkill = !selectedSkill || skills.includes(selectedSkill);

        if (matchesSearch && matchesSkill) {
          card.style.display = 'block';
        } else {
          card.style.display = 'none';
        }
      });
    };

    if (searchInput) searchInput.addEventListener('input', filterJobs);
    if (skillFilterSelect) skillFilterSelect.addEventListener('change', filterJobs);
  }
});
