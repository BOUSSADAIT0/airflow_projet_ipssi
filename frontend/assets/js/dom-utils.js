// dom-utils.js
export class DOMHelper {
    static getElement(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Element #${id} not found`);
            return null;
        }
        return element;
    }
    
    static getElements(selector) {
        const elements = document.querySelectorAll(selector);
        if (elements.length === 0) {
            console.warn(`No elements found for selector: ${selector}`);
        }
        return elements;
    }
    
    static safeInnerHTML(element, html) {
        if (element) {
            element.innerHTML = html;
        }
    }
    
    static safeAddEventListener(element, event, handler) {
        if (element) {
            element.addEventListener(event, handler);
            return true;
        }
        return false;
    }
}

// Usage dans votre code principal :
// const container = DOMHelper.getElement('resultsContainer');
// DOMHelper.safeInnerHTML(container, '<p>Contenu</p>');