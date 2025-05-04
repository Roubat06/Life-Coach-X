document.addEventListener('DOMContentLoaded', function() {
    const dietForm = document.getElementById('dietForm');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultSection = document.getElementById('resultSection');
    const dietPlanElement = document.getElementById('dietPlan');

    dietForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Validate form
        const requiredFields = ['name', 'age', 'gender', 'weight', 'height', 'activity', 'goal'];
        let isValid = true;
        
        requiredFields.forEach(field => {
            const element = document.getElementById(field);
            if (!element.value) {
                element.classList.add('border-red-500');
                isValid = false;
            } else {
                element.classList.remove('border-red-500');
            }
        });
        
        if (!isValid) {
            alert('Please fill out all required fields');
            return;
        }
        
        // Show loading indicator
        loadingIndicator.classList.remove('hidden');
        resultSection.classList.add('hidden');
        
        // Collect form data
        const formData = new FormData(dietForm);
        
        // Handle checkboxes for dietary restrictions
        const restrictionCheckboxes = document.querySelectorAll('input[name="restrictions"]:checked');
        const restrictions = Array.from(restrictionCheckboxes).map(cb => cb.value);
        
        // Create request payload
        const payload = {
            name: formData.get('name'),
            age: parseInt(formData.get('age')),
            gender: formData.get('gender'),
            weight: parseFloat(formData.get('weight')), 
            height: parseInt(formData.get('height')),
            activity_level: formData.get('activity'),
            goal: formData.get('goal'),
            dietary_restrictions: restrictions,
            allergies: formData.get('allergies'),
            preferences: formData.get('preferences')
        };
        
        console.log("Sending data to backend:", payload);
        
        try {
            // Send request to backend
            const response = await fetch('/generate_diet_plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to generate diet plan');
            }
            
            console.log("Received response:", data);
            
            // Display the result
            if (data.diet_plan) {
                dietPlanElement.innerHTML = markdownToHtml(data.diet_plan);
                resultSection.classList.remove('hidden');
                
                // Scroll to results
                resultSection.scrollIntoView({ behavior: 'smooth' });
            } else {
                throw new Error('No diet plan received from the server');
            }
        } catch (error) {
            console.error('Error:', error);
            alert(`An error occurred: ${error.message}`);
        } finally {
            // Hide loading indicator
            loadingIndicator.classList.add('hidden');
        }
    });
    
    // Simple markdown to HTML converter for basic formatting
    function markdownToHtml(markdown) {
        if (!markdown) return '';
        
        // Convert headers
        markdown = markdown.replace(/^### (.*$)/gim, '<h3 class="text-lg font-bold mt-4 mb-2">$1</h3>');
        markdown = markdown.replace(/^## (.*$)/gim, '<h2 class="text-xl font-bold mt-6 mb-3">$1</h2>');
        markdown = markdown.replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>');
        
        // Convert bold text
        markdown = markdown.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
        
        // Convert italic text
        markdown = markdown.replace(/\*(.*?)\*/gim, '<em>$1</em>');
        
        // Convert lists
        markdown = markdown.replace(/^\s*\-\s*(.*$)/gim, '<li class="ml-4">$1</li>');
        markdown = markdown.replace(/^\s*\d+\.\s*(.*$)/gim, '<li class="ml-4">$1</li>');
        
        // Group list items
        markdown = markdown.replace(/(<li.*<\/li>)\s*(<li)/gim, '$1\n<$2');
        markdown = markdown.replace(/(<li.*<\/li>)\s*(?!<li)/gim, '<ul class="list-disc mb-4">$1</ul>');
        
        // Convert line breaks
        markdown = markdown.replace(/\n\n/gim, '<br><br>');
        
        return markdown;
    }
});